#! /usr/bin/env python3

import fcntl
import time
import os
# python 2 compatibility
try:
    from urllib.parse import quote, unquote
except:
    from urllib import quote, unquote
from . import config

house = config.get('global', 'house_team')
passwdfn = config.get('global', 'passwd')
team_colors = config.get('global', 'team_colors')

teams = {}
built = 0
def build_teams():
    global teams, built
    if not os.path.exists(passwdfn):
        return
    if os.path.getmtime(passwdfn) <= built:
        return

    teams = {}
    try:
        f = open(passwdfn)
        for line in f:
            line = line.strip()
            team, passwd, color = map(unquote, line.strip().split('\t'))
            teams[team] = (passwd, color)
    except IOError:
        pass
    built = time.time()

def validate(team):
    build_teams()

def chkpasswd(team, passwd):
    validate(team)
    if teams.get(team, [None, None])[0] == passwd:
        return True
    else:
        return False

def exists(team):
    validate(team)
    if team == house:
        return True
    return team in teams

def add(team, passwd):
    build_teams()
    color = team_colors[len(teams)%len(team_colors)]

    assert team not in teams, "Team already exists."

    f = open(passwdfn, 'a')
    fcntl.lockf(f, fcntl.LOCK_EX)
    f.seek(0, 2)
    f.write('%s\t%s\t%s\n' % (quote(team), quote(passwd), quote(color)))

def color(team):
    t = teams.get(team)
    if not t:
        validate(team)
        t = teams.get(team)
        if not t:
            return '888888'
    return t[1]
