#!/usr/bin/env python
# coding: utf-8

# Bits of information I need:
# - Player rankings
# - How each player did in last year's tournament
# - What the draw looks like this year

from collections import OrderedDict
from itertools import groupby, ifilter
import re

import mwparserfromhell
import requests
import requests_cache
from bs4 import BeautifulSoup

requests_cache.install_cache('.cache')

EU_RANKINGS = 'http://live-tennis.eu/official_atp_ranking'


class DoubleAddExeption(Exception):
    pass


class PlayerPool(object):
    def __init__(self):
        self._players = []

    def getPlayer(self, playerName):
        candidates = [p for p in self._players if p.name == playerName]
        if len(candidates) == 0:
            raise KeyError('No player named %s in cache.' % playerName)
        return candidates[0]

    def addPlayer(self, player):
        try:
            p = self.getPlayer(player.name)
        except KeyError:
            self._players.append(player)
        else:
            raise DoubleAddException('Tried to add %s twice' % player.name)

    def getOrAdd(self, name, nationality):
        try:
            return self.getPlayer(name)
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
        return _player_pool.getPlayer(name)


class RankedPlayer(object):
    def __init__(self, player, rank, points):
        self.player = player
        self.rank = rank
        self.points = points


class Rankings(object):
    def __init__(self):
        r = requests.get(EU_RANKINGS)
        self._rankings = []
        self._parseRankings(r.content)

    def getPlayerAtRank(self, rank):
        return self._rankings[rank]

    def rankingForPlayer(self, playerName):
        p = _player_pool.getPlayer(playerName)
        ps = [r for r in self._rankings if r.player == p]
        return ps[0]

    def _parseRankings(self, html):
        bs = BeautifulSoup(html)
        rows = bs.select('#playerRankings table table tr')
        for row in rows:
            # cell1 is the ranking, e.g. 1, 2, 3
            cells = row.select('td')
            cell1 = cells[0].text.strip()
            if not re.match(r'^[0-9]+$', cell1): continue

            rank = int(cell1)
            name = cells[2].text
            nationality = cells[3].text
            points = int(cells[4].text)
            p = _player_pool.getOrAdd(name, nationality)
            self._rankings.append(RankedPlayer(p, rank, points))


class Tournament(object):
    API_URL = "http://en.wikipedia.org/w/api.php"
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
        wikitext = r.json()["query"]["pages"].values()[0]["revisions"][0]["*"]
        wikicode = mwparserfromhell.parse(wikitext)

        self._extract_from_wikicode(wikicode)


    def getResultForPlayer(self, p):
        name = p.name
        facts = filter(lambda f: f[2] == name, self._facts)
        rounds = [r[0] for r in facts]
        return rounds

    @staticmethod
    def _make_url(year, tournament):
        return "%s %s – Men's Singles" % (year, tournament)

    def _extract_from_wikicode(self, wikicode):
        facts = []
        items = []

        for section in wikicode.get_sections():
            wc = mwparserfromhell.parse(section.encode('utf8'))
            templates = wc.filter_templates()
            bracket = next(ifilter(lambda t: 'Bracket' in t.name, templates), None)
            if bracket:
                items.append(bracket)
        brackets = [key for key,_ in groupby(items)]
        self._brackets = brackets
        for bracket in brackets:
            facts.extend(Tournament._facts_from_bracket(bracket))

        self._facts = facts

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
            k, v = p.name.strip(), p.value.strip()
            m = re.match(r'(RD\d+)-team(\d+)', unicode(k))
            if m:
                roundId, slot = m.groups()

                roundName = rounds[roundId]

                w = mwparserfromhell.parse(v.encode('utf8'))
                # need to strip out {{nowrap}} templates
                playerName = re.sub(r'\|.*', '', w.strip_code().strip())

                flag_template = next(ifilter(lambda t: 'flagicon' == t.name, w.filter_templates()))
                nationality = flag_template.params[0].value

                facts.append((roundName, slot, playerName, nationality))

        return facts


if __name__ == '__main__':
    rankings = Rankings()
