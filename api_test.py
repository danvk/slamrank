# coding: utf-8
from nose.tools import *

import api


def test_Rankings():
    r = api.Rankings()  # fills player cache
    p = api.Player.get('Roger Federer')
    eq_('SUI', p.nationality)


def test_TournamentUrl():
    eq_("2014 Australian Open – Men's Singles",
            api.Tournament._make_url(2014, api.Tournament.AUSTRALIAN))
    eq_("1999 French Open – Men's Singles",
            api.Tournament._make_url(1999, api.Tournament.FRENCH))

def test_Tournament():
    t = api.Tournament(2014, api.Tournament.AUSTRALIAN)

    result = t.getResultForPlayer(api.Player.get('Rafael Nadal'))
    print result
    eq_('F', result.code)
