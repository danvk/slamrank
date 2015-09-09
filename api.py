#!/usr/bin/env python
# coding: utf-8

# Bits of information I need:
# - Player rankings
# - How each player did in last year's tournament
# - What the draw looks like this year

from collections import OrderedDict
from itertools import groupby, ifilter
import re
from datetime import datetime

import mwparserfromhell
import requests
import requests_cache
from bs4 import BeautifulSoup
from unidecode import unidecode

requests_cache.install_cache('.cache')

EU_RANKINGS = 'http://live-tennis.eu/official_atp_ranking'
ATP_RANKINGS = 'http://www.atpworldtour.com/en/rankings/singles?rankRange=1-1500'


class DoubleAddExeption(Exception):
    pass


# Key is wikipedia article title (minus accents), value is ATP player name.
shims = {
    'Pablo Carreno': 'Pablo Carreno Busta',
    'Lu Yen-hsun': 'Yen-Hsun Lu',
    'Albert Ramos': 'Albert Ramos-Vinolas',
    'Chung Hyeon': 'Hyeon Chung'
}


class PlayerPool(object):
    def __init__(self):
        self._players = []

    def get_player(self, player_name):
        names = set([player_name])
        alt_name = shims.get(player_name)
        if alt_name:
            names.add(alt_name)
        candidates = [p for p in self._players if p.name in names]
        if len(candidates) == 0:
            raise KeyError(u'No player named %s in cache.' % player_name)
        return candidates[0]

    def addPlayer(self, player):
        try:
            p = self.get_player(player.name)
        except KeyError:
            self._players.append(player)
        else:
            raise DoubleAddException('Tried to add %s twice' % player.name)

    def getOrAdd(self, name, nationality):
        try:
            return self.get_player(name)
        except KeyError as e:
            p = Player(name, nationality)
            self.addPlayer(p)
            return p


_player_pool = PlayerPool()


class Player(object):
    def __init__(self, name, nationality):
        self.name = name
        self.nationality = nationality

    @staticmethod
    def get(name):
        return _player_pool.get_player(name)

    def __repr__(self):
        return '%s (%s)' % (self.name, self.nationality)


class RankedPlayer(object):
    def __init__(self, player, rank, points, points_dropping):
        self.player = player
        self.rank = rank
        self.points = points
        self.points_dropping = points_dropping

    @property
    def name(self):
        return self.player.name

    @property
    def nationality(self):
        return self.player.nationality

    def __repr__(self):
        return '#%s %s (%s, %s dropping %s)' % (
                self.rank, self.name, self.nationality, self.points, self.points_dropping)


class Rankings(object):
    def __init__(self):
        r = requests.get(ATP_RANKINGS)
        self._rankings = []
        self._parseRankings(r.content)

    def get_player_at_rank(self, rank):
        return self._rankings[rank]

    def ranking_for_player(self, player_name):
        p = _player_pool.get_player(player_name)
        ps = [r for r in self._rankings if r.player == p]
        return ps[0]

    def _parseRankings(self, html):
        def select_one(soup, selector):
            el = soup.select(selector)
            assert len(el) == 1
            return el[0]

        bs = BeautifulSoup(html, 'html.parser')
        rows = bs.select('#singlesRanking tbody tr')
        for row in rows:
            rank = int(select_one(row, '.rank-cell').text.strip().replace('T', ''))
            nationality = select_one(row, '.country-item img')['alt']
            name = select_one(row, '.player-cell').text.strip()
            points = int(select_one(row, '.points-cell').text.strip().replace(',', ''))
            points_dropping = int(select_one(row, '.pts-cell').text.strip().replace(',', ''))

            p = _player_pool.getOrAdd(name, nationality)
            self._rankings.append(RankedPlayer(p, rank, points, points_dropping))


class UnfilledException(Exception):
    pass


class Tournament(object):
    API_URL = 'http://en.wikipedia.org/w/api.php'
    AUSTRALIAN = 'Australian Open'
    FRENCH = 'French Open'
    WIMBLEDON = 'Wimbledon'
    US_OPEN = 'US Open'

    def __init__(self, year, tournament):
        assert tournament in [
                Tournament.AUSTRALIAN,
                Tournament.FRENCH,
                Tournament.WIMBLEDON,
                Tournament.US_OPEN]
        assert 1884 <= year <= 2050

        # TODO: Parse the wiki markup using mwparserfromhell.
        # See https://github.com/earwig/mwparserfromhell/issues/84
        r = requests.get(Tournament.API_URL, params={
            'action': 'query',
            'prop': 'revisions',
            'rvlimit': 1,
            'rvprop': 'content',
            'format': 'json',
            'titles': Tournament._make_url(year, tournament)})
        wikitext = r.json()['query']['pages'].values()[0]['revisions'][0]['*']
        wikicode = mwparserfromhell.parse(wikitext, skip_style_tags=True)

        self._extract_from_wikicode(wikicode)

    def get_result_for_player(self, p):
        name = p.name
        facts = filter(lambda f: f[2] == name, self._facts)
        rounds = [r[0] for r in facts]
        return rounds

    def players(self):
        players = set()
        for i, fact in enumerate(self._facts):
            name = fact[2]
            name_no_accents = unidecode(name)
            try:
                player = Player.get(name_no_accents)
                players.add(player)
            except KeyError:
                print 'Missing %s' % name_no_accents
        return players

    @staticmethod
    def _make_url(year, tournament):
        return "%s %s – Men's Singles" % (year, tournament)

    def _extract_from_wikicode(self, wikicode):
        facts = []
        items = []

        templates = wikicode.filter_templates()
        self._brackets = []
        for bracket in filter(lambda t: 'Bracket' in t.name, templates):
            self._brackets.append(bracket)
            facts.extend(Tournament._facts_from_bracket(bracket))

        self._facts = facts

    @staticmethod
    def _facts_from_team(team_value):
        '''Given a RDx-team value, return a (player, nationality) tuple.'''
        links = team_value.filter_wikilinks()
        if len(links) != 1:
            raise UnfilledException(team_value)
        name = links[0].title.strip_code()
        name = re.sub(r' \(.*', '', name)  # e.g. 'Kevin Anderson (tennis)'

        flags = [t for t in team_value.filter_templates() if t.name == 'flagicon']
        assert len(flags) == 1
        nationality = flags[0].params[0]

        return name, nationality

    @staticmethod
    def _facts_from_bracket(bracket):
        rounds = {}
        try:
            for i in range(1, 7):
                p = bracket.get('RD%s' % i)
                rounds[unicode(p.name.strip())] = p.value.strip()
        except ValueError:
            pass  # no such round

        facts = []
        for p in bracket.params:
            k, v = p.name.strip(), p.value
            m = re.match(r'(RD\d+)-team(\d+)', unicode(k))
            if m:
                roundId, slot = m.groups()

                roundName = rounds[roundId]

                try:
                    name, nationality = Tournament._facts_from_team(v)
                    facts.append((roundName, slot, name, nationality))
                except UnfilledException:
                    pass

        return facts


def load_players_and_tourney(year, tournament):
    r = Rankings()
    t = Tournament(year, tournament)
    return r, t


if __name__ == '__main__':
    rankings = Rankings()
