#!/usr/bin/env python
# coding: utf-8

# Bits of information I need:
# - Player rankings
# - How each player did in last year's tournament
# - What the draw looks like this year

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

    def __init__(self, wikiTitle):
        # TODO: Parse the wiki markup using mwparserfromhell.
        # See https://github.com/earwig/mwparserfromhell/issues/84
        r = requests.get(Tournament.API_URL, params={
            'action': 'query',
            'prop': 'revisions',
            'rvlimit': 1,
            'rvprop': 'content',
            'format': 'json',
            'titles': wikiTitle})
        wikitext = r.json()["query"]["pages"].values()[0]["revisions"][0]["*"]
        wikicode = mwparserfromhell.parse(wikitext)

        self._extract_from_wikicode(wikicode)

    def _extract_from_wikicode(self, wikicode):
        facts = ()

        for section in wikicode.get_sections():
            wc = mwparserfromhell.parse(section.encode('utf8'))
            templates = wc.filter_templates()


if __name__ == '__main__':
    rankings = Rankings()
