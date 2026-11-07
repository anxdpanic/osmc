# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.apfstore

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    The App Store's data: the apps offered for this device and whether they are installed.

    =========================
    APF JSON STRUCTURE
    =========================
    {
       "application": [
           {
               "id": "ssh-app-osmc",
               "name": "SSH Server",
               "shortdesc": "This allows you to connect to your OSMC device via SSH",
               "longdesc": "This installs an OpenSSH server on your OSMC device ...",
               "maintained-by": "OSMC",
               "version": "1.0.0",
               "lastupdated": "2015-01-23",
               "iconurl": "http://blah",   (or "NA")
               "iconhash": 0               (or "NA")
           }
       ]
    }
"""

import datetime
import json
import os
import subprocess
from io import open

import requests

import xbmcaddon
from osmccommon.osmc_logging import StandardLogger

ADDON_ID = 'script.module.osmcsetting.apfstore'
URL_BASE = 'https://download.osmc.tv/apps/%s'
DEFAULT_DEVICE = 'rbp2'

CACHE_TIMEOUT = datetime.timedelta(hours=6)
TIME_STRING_PATTERN = '%Y/%m/%d %H:%M:%S'

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


class App(object):

    def __init__(self, data, default_icon=''):
        self.id = data.get('id', '')
        self.name = data.get('name', self.id)
        self.shortdesc = data.get('shortdesc', '')
        self.longdesc = data.get('longdesc', '')
        self.maintainedby = data.get('maintained-by', '')
        self.version = data.get('version', '')
        self.lastupdated = data.get('lastupdated', '')

        iconurl = data.get('iconurl', 'NA')
        # Kodi downloads and caches remote art itself
        self.icon = iconurl if iconurl and iconurl != 'NA' and '://' in iconurl else default_icon

        self.installed = False


def device():
    """ The device name from osmcdev= in /proc/cmdline, e.g. vero5 or rbp2 """
    try:
        with open('/proc/cmdline', 'r', encoding='utf-8') as open_file:
            for setting in open_file.read().split():
                if setting.startswith('osmcdev='):
                    return setting[len('osmcdev='):]
    except (IOError, OSError):
        pass
    return DEFAULT_DEVICE


def is_unsupported_alpha():
    """ Alpha 4 and earlier cannot use the App Store """
    with open(os.devnull, 'w') as devnull:
        return subprocess.call(['/usr/bin/dpkg-query', '-l', 'rbp-mediacenter-osmc'],
                               stdout=devnull, stderr=devnull) == 0


def installed_packages(package_ids):
    """ The subset of package_ids that dpkg reports as installed """
    if not package_ids:
        return set()

    with open(os.devnull, 'w') as devnull:
        try:
            output = subprocess.check_output(
                ['dpkg-query', '-W', '-f=${Package} ${Status}\n'] + list(package_ids),
                stderr=devnull)
        except subprocess.CalledProcessError as error:
            # dpkg-query exits non-zero when any package is unknown, but still lists the others
            output = error.output or b''

    if isinstance(output, bytes):
        output = output.decode('utf-8', 'ignore')

    installed = set()
    for line in output.splitlines():
        parts = line.split(' ', 1)
        if len(parts) == 2 and parts[1].strip().endswith('ok installed'):
            installed.add(parts[0])
    return installed


class Store(object):

    def __init__(self, addon=None):
        self._addon = addon
        self.default_icon = os.path.join(self.addon.getAddonInfo('path'),
                                         'resources', 'media', 'osmc_logo.png')

    @property
    def addon(self):
        if not self._addon:
            self._addon = xbmcaddon.Addon(ADDON_ID)
        return self._addon

    def _cached(self, fresh_only):
        raw = self.addon.getSetting('json_cache')
        if not raw or raw == 'empty':
            return None

        if fresh_only:
            try:
                updated = datetime.datetime.strptime(self.addon.getSetting('json_lastupdated'),
                                                     TIME_STRING_PATTERN)
            except (TypeError, ValueError):
                return None
            if datetime.datetime.now() - updated > CACHE_TIMEOUT:
                return None

        try:
            return json.loads(raw)
        except ValueError:
            return None

    def _download(self):
        url = URL_BASE % device()
        log('APF data URL: %s' % url)
        try:
            response = requests.get(url, timeout=15)
            payload = response.json()
        except Exception as error:
            log('Failed to retrieve %s: %s' % (url, error))
            return None

        self.addon.setSetting('json_cache', json.dumps(payload))
        self.addon.setSetting('json_lastupdated',
                              datetime.datetime.now().strftime(TIME_STRING_PATTERN))
        return payload

    def data(self, refresh=False):
        """ The app list: the cache while it is fresh, else the server, else any cache """
        payload = None if refresh else self._cached(fresh_only=True)
        if payload is None:
            payload = self._download()
        if payload is None:
            payload = self._cached(fresh_only=False)
        return payload

    def apps(self, refresh=False):
        """ The apps in the store's order, with their install status; None if unavailable """
        payload = self.data(refresh=refresh)
        if payload is None:
            return None

        apps = [App(item, self.default_icon) for item in payload.get('application', [])
                if item.get('id')]

        installed = installed_packages([app.id for app in apps])
        for app in apps:
            app.installed = app.id in installed

        return apps

    def app(self, app_id):
        for app in self.apps() or []:
            if app.id == app_id:
                return app
        return None
