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
import json

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
        assert len(candidates) == 1
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

    def to_json(self):
        return {
            'name': self.name,
            'nationality': self.nationality,
            'rank': self.rank,
            'points': self.points,
            'points_dropping': self.points_dropping
        }


class Rankings(object):
    def __init__(self):
        r = requests.get(ATP_RANKINGS)
        self._rankings = []
        self._parseRankings(r.content)

    def get_player_at_rank(self, rank):
        return self._rankings[rank]

    def ranking_for_player(self, player_name):
        p = _player_pool.get_player(player_name)
        return self.ranked_player(p)

    def ranked_player(self, player):
        ps = [r for r in self._rankings if r.player == player]
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

    ROUND_INDICES = {
      'First Round': 0,
      'Second Round': 1,
      'Third Round': 2,
      'Fourth Round': 3,
      'Quarterfinals': 4,
      'Semifinals': 5,
      'Final': 6
    }

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

    def get_last_round_for_player(self, player):
        for idx, players in reversed(list(enumerate(self._rounds))):
            if player in players:
                return idx
        raise KeyError('Player %s is not in this tournament' % player)

    def players(self):
        return set((p for _, _, p in self._facts if p))

    @staticmethod
    def _make_url(year, tournament):
        return "%s %s – Men's Singles" % (year, tournament)

    def _extract_from_wikicode(self, wikicode):
        facts = []
        items = []

        templates = wikicode.filter_templates()
        self._brackets = []
        self._rounds = [[] for i in range(0, 7)]
        for bracket in filter(lambda t: 'Bracket' in t.name, templates):
            self._brackets.append(bracket)
            section_facts = Tournament._facts_from_bracket(bracket)
            for round_name, _, player in section_facts:
                self._rounds[Tournament.ROUND_INDICES[round_name]].append(player)
            facts.extend(section_facts)

        self._facts = facts

    @staticmethod
    def _facts_from_team(team_value):
        '''Given a RDx-team value, return a (player, nationality) tuple.'''
        links = team_value.filter_wikilinks()
        if len(links) != 1:
            raise UnfilledException(team_value)
        name = links[0].title.strip_code()
        name = re.sub(r' \(.*', '', name)  # e.g. 'Kevin Anderson (tennis)'
        name_no_accents = unidecode(name)
        player = Player.get(name_no_accents)

        flags = [t for t in team_value.filter_templates() if t.name == 'flagicon']
        assert len(flags) == 1
        nationality = flags[0].params[0]
        assert player.nationality == nationality

        return player

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
                    player = Tournament._facts_from_team(v)
                    facts.append((roundName, slot, player))
                except UnfilledException:
                    facts.append((roundName, slot, None))

        return facts

    def to_json(self, rankings):
        players = list((rankings.ranked_player(p) for p in self.players()))
        players.sort(key=lambda p: p.rank)

        player_to_idx = {rp.player: idx for idx, rp in enumerate(players)}

        # this is a list of players in each round
        rounds = [[player_to_idx.get(p) if p else None for p in rnd] for rnd in self._rounds]
        matches = [zip(ps[::2], ps[1::2]) for ps in rounds]

        return {
            'players': [p.to_json() for p in players],
            'matches': matches
        }


def load_players_and_tourney(year, tournament):
    r = Rankings()
    t = Tournament(year, tournament)
    return r, t


if __name__ == '__main__':
    rankings, tourney = load_players_and_tourney(2015, 'US Open')
    open('2015usopen.js', 'wb').write((u'var data = %s;' % json.dumps(tourney.to_json(rankings), indent=2)).encode('utf8'))
