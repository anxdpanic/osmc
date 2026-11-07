# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.networking

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    Run by the My OSMC settings service every few seconds: while the Wi-Fi folder
    is showing, refresh it when what it shows has changed, and search for networks
    now and then so the list stays current.
"""

import os
import time

import xbmc
from osmccommon.osmc_logging import StandardLogger

from . import osmc_network
from . import plugin

ADDON_ID = 'script.module.osmcsetting.networking'
SEARCH_INTERVAL = 30  # seconds between searches while the folder shows

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


def is_wifi_folder(folder_path):
    return (folder_path.startswith(plugin.BASE_URL) and
            'module=%s' % plugin.MODULE_ID in folder_path and
            'folder=%s' % plugin.WIFI_FOLDER in folder_path)


def wifi_signature():
    """ What the Wi-Fi folder shows, so a change can be spotted """
    if not osmc_network.is_wifi_enabled():
        return ('off',)

    return tuple((n['path'], n['connected'], n['saved'], n['security'],
                  plugin.signal_level(n['strength']))
                 for n in plugin.visible_networks(osmc_network.wifi_services()))


class Watcher(object):

    def __init__(self):
        self.signature = None
        self.last_search = 0

    def poll(self):
        if not is_wifi_folder(xbmc.getInfoLabel('Container.FolderPath')):
            self.signature = None
            return

        now = time.time()
        if now - self.last_search > SEARCH_INTERVAL and osmc_network.is_wifi_enabled():
            self.last_search = now
            osmc_network.scan_wifi()

        signature = wifi_signature()
        if self.signature is not None and signature != self.signature:
            # leave the folder alone while a dialog (a password, a question) is open
            if xbmc.getCondVisibility('System.HasActiveModalDialog'):
                return
            log('Wi-Fi changed, refreshing the folder')
            xbmc.executebuiltin('Container.Refresh')
        self.signature = signature
