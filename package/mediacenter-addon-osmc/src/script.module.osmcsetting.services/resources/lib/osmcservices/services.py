# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.services

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    Services: Dialog().multiselect over /etc/osmc/apps.d, every running or
    enabled service preselected. OK enables and starts what was newly selected,
    disables and stops what was cleared; Cancel or Back changes nothing.
"""

import os
import subprocess
from io import open

import xbmcaddon
import xbmcgui
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger
from osmccommon.osmc_logging import clog

ADDON_ID = 'script.module.osmcsetting.services'
APPS_DIRECTORY = '/etc/osmc/apps.d'

SYSTEMCTL = '/bin/systemctl'

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


class Service(object):

    def __init__(self, name, units):
        self.name = name  # the friendly name, first line of the apps.d file
        self.units = units  # the systemd units, one per following line
        self.running = False
        self.enabled = False
        self.update()

    @staticmethod
    def _systemctl(*args):
        with open(os.devnull, 'w') as devnull:
            return subprocess.call(['sudo', SYSTEMCTL] + list(args), stdout=devnull, stderr=devnull)

    def update(self):
        self.running = all(self._systemctl('is-active', unit) == 0 for unit in self.units)
        self.enabled = all(self._systemctl('is-enabled', unit) == 0 for unit in self.units)

    @property
    def active(self):
        """ running or enabled: preselected in the list """
        return self.running or self.enabled

    @clog(log)
    def enable(self):
        for unit in self.units:
            self._systemctl('enable', unit)
            self._systemctl('start', unit)
        self.update()
        return self.running

    @clog(log)
    def disable(self):
        for unit in self.units:
            self._systemctl('disable', unit)
            self._systemctl('stop', unit)
        self.update()
        return not self.active


@clog(log, maxlength=500)
def discover_services(directory=APPS_DIRECTORY):
    """ The services in apps.d, sorted by their friendly name """
    services = []

    if not os.path.isdir(directory):
        return services

    for file_name in os.listdir(directory):
        file_path = os.path.join(directory, file_name)
        if not os.path.isfile(file_path):
            continue

        with open(file_path, encoding='utf-8') as open_file:
            lines = [line.strip() for line in open_file.readlines() if line.strip()]

        if len(lines) < 2:
            log('Skipping %s, no service listed' % file_path)
            continue

        log('Service %s: %s' % (lines[0], lines[1:]))
        services.append(Service(lines[0], lines[1:]))

    return sorted(services, key=lambda s: s.name.lower())


class Services(object):

    def __init__(self, addon=None):
        self._addon = addon
        self._lang = None
        self.dialog = xbmcgui.Dialog()

    @property
    def addon(self):
        if not self._addon:
            self._addon = xbmcaddon.Addon(ADDON_ID)
        return self._addon

    def lang(self, value):
        if not self._lang:
            self._lang = LangRetriever(self.addon).lang
        return self._lang(value)

    def state(self, service):
        if service.running:
            return self.lang(32009)  # running
        if service.enabled:
            return self.lang(32010)  # enabled
        return self.lang(32011)  # stopped

    def run(self):
        services = discover_services()

        items = []
        for service in services:
            list_item = xbmcgui.ListItem(label='%s  [LIGHT]•  %s[/LIGHT]' %
                                               (service.name, self.state(service)),
                                         offscreen=True)
            items.append(list_item)

        preselect = [index for index, service in enumerate(services) if service.active]

        selected = self.dialog.multiselect(self.lang(32012), items, preselect=preselect)
        if selected is None:
            log('Services: cancelled')
            return

        messages = []
        for index, service in enumerate(services):
            wanted = index in selected
            if wanted and not service.active:
                if service.enable():
                    messages.append(self.lang(32013) % service.name)  # started
                else:
                    messages.append(self.lang(32015) % service.name)  # could not start
            elif not wanted and service.active:
                if service.disable():
                    messages.append(self.lang(32014) % service.name)  # stopped
                else:
                    messages.append(self.lang(32016) % service.name)  # could not stop

        if messages:
            self.dialog.notification(self.lang(32012), ', '.join(messages))


def run(addon=None):
    Services(addon).run()
