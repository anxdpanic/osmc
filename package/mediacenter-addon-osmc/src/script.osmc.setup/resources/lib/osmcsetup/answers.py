# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.osmc.setup

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    The setup's answers and its step order, without Kodi, so they can be tested alone.
"""

import random
import re

# every step, in order; steps() leaves out the ones a device does not show
STEPS = ['remote', 'language', 'network', 'timezone', 'device', 'ssh',
         'newsletter', 'warranty', 'license', 'summary']

HOSTNAME_MAX = 63
HOSTNAME_CHARACTERS = re.compile(r'^[A-Za-z0-9-]+$')
EMAIL = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

# hostname problems, named by the rule they break
NAME_EMPTY = 'empty'
NAME_CHARACTERS = 'characters'
NAME_HYPHEN = 'hyphen'
NAME_LENGTH = 'length'

RANDOM_NAMES = [
    'Alfonse', 'Barnaby', 'Aloysius', 'Archibald', 'Algernon', 'Basil', 'Bertram',
    'Carston', 'Cavendish', 'Cecil', 'Cyril', 'Danforth', 'Cuthbert', 'Alastair',
    'Preston', 'Giles', 'Cortland', 'Atticus', 'Edmund', 'Gilbert', 'Ethelbert',
    'Frederick', 'Geoffrey', 'Gideon', 'Giggleswick', 'Grumbole', 'Hamilton', 'Ignatius',
    'Ebenezer', 'Herbert', 'Clement', 'Humphrey', 'Ian', 'Ichabod', 'Jonathan', 'Malcolm',
    'Mervyn', 'Mortimer', 'Nigel', 'Percy', 'Prentis', 'Reginald', 'Ridgewell', 'Royston',
    'Theophilus', 'Tobias', 'Tristram', 'Ulysses', 'Ulrich', 'Virgil', 'Vivian', 'Waldo',
    'Wesley', 'Wilbur', 'Wilfred', 'Willard', 'Willoughby',
]


def hostname_problem(name):
    """ None for a valid hostname, otherwise the rule it breaks """
    if not name:
        return NAME_EMPTY
    if len(name) > HOSTNAME_MAX:
        return NAME_LENGTH
    if not HOSTNAME_CHARACTERS.match(name):
        return NAME_CHARACTERS
    if name.startswith('-') or name.endswith('-'):
        return NAME_HYPHEN
    return None


def random_name(current=None):
    """ A random osmc-<name>, never the current one """
    names = [n for n in RANDOM_NAMES if 'osmc-' + n != current]
    return 'osmc-' + random.choice(names)


def is_email(address):
    return bool(address and EMAIL.match(address))


class Answers(object):
    """ What setup has been told so far, and where it is """

    def __init__(self, vero=False, online=False, hostname='osmc'):
        self.vero = vero
        self.online = online

        self.step = 'remote'
        self.furthest = 'remote'

        # language and region, as Kodi names them (labels) and stores them (values)
        self.language = ''
        self.language_label = ''
        self.region = ''

        # network, as the summary shows it: ('wifi', ssid), ('wired', None) or (None, None)
        self.connection = (None, None)

        self.timezone_country = ''
        self.timezone = ''
        self.testing = False  # "Test walk through" from My OSMC: Finish applies nothing
        self.failed = False  # the window could not be drawn
        self.timezone_detected = False  # the lookup was tried
        self.timezone_found = False  # and it gave the country and timezone

        self.original_hostname = hostname
        self.hostname = hostname

        self.ssh = True
        self.ssh_password = None  # None leaves the password unchanged

        self.newsletter = False
        self.email = ''

        self.check_updates = True

        # set when a new language needs the window to reopen
        self.pending_language = None
        self.finished = False

    # ---- step order ----------------------------------------------------------------------

    def steps(self):
        steps = list(STEPS)
        if not self.online:
            steps.remove('newsletter')
        if not self.vero:
            steps.remove('warranty')
        return steps

    def position(self, step=None):
        """ The 0-based place of a step among those shown; one that left the order
            (Newsletter going offline) counts as the step before it """
        return self.steps().index(self._known(step or self.step))

    def _known(self, step):
        """ A step that left the order (Newsletter going offline) falls back to the one before """
        steps = self.steps()
        if step in steps:
            return step
        index = STEPS.index(step)
        while index > 0:
            index -= 1
            if STEPS[index] in steps:
                return STEPS[index]
        return steps[0]

    def has_back(self):
        """ Remote has no Back """
        return self.position() > 0

    def back(self):
        """ The previous step; Remote stays put """
        if not self.has_back():
            return self.step
        self.step = self.steps()[self.position() - 1]
        return self.step

    def done(self):
        """ The next step: the furthest reached, when this one was reached again with Back """
        self.furthest = self._known(self.furthest)
        steps = self.steps()
        here = self.position()
        furthest = steps.index(self.furthest)
        if here < furthest:
            self.step = self.furthest
        elif here + 1 < len(steps):
            self.step = steps[here + 1]
            self.furthest = self.step
        return self.step

    # ---- summary -------------------------------------------------------------------------

    def summary(self, lang):
        """ (title, choice) pairs; lang turns a string id into text """
        connection, name = self.connection
        if connection == 'wifi':
            network = lang(32147) % name  # Wi-Fi, <name>
        elif connection == 'wired':
            network = lang(32106)  # Wired
        else:
            network = lang(32132)  # Not connected

        rows = [
            (lang(32102), self.language_label),  # Language
            (lang(32103), self.region),  # Region
            (lang(32104), network),  # Network
            (lang(32107), self.timezone_country),  # Timezone country
            (lang(32009), self.timezone),  # Timezone
            (lang(32108), self.hostname),  # Device name
            (lang(32110), lang(32143) if self.ssh else lang(32144)),  # SSH server On/Off
        ]
        if self.online:
            rows.append((lang(32112), self.email if self.newsletter else lang(32144)))
        return rows
