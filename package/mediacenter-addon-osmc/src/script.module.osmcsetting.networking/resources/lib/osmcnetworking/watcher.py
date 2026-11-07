# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.networking

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    Run by the My OSMC settings service every few seconds: while the Wi-Fi or
    Bluetooth folder is showing, refresh it when what it shows has changed. Wi-Fi
    searches for networks now and then; Bluetooth searches for devices for as long
    as its folder shows.
"""

import os
import time

import xbmc
import xbmcaddon
from osmccommon.osmc_logging import StandardLogger

from . import osmc_network
from . import plugin

ADDON_ID = 'script.module.osmcsetting.networking'
SEARCH_INTERVAL = 30  # seconds between searches while the folder shows

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


def showing_folder(folder_path):
    """ 'wifi', 'bluetooth' or None """
    if not (folder_path.startswith(plugin.BASE_URL) and
            'module=%s' % plugin.MODULE_ID in folder_path):
        return None
    for folder in (plugin.WIFI_FOLDER, plugin.BLUETOOTH_FOLDER):
        if 'folder=%s' % folder in folder_path:
            return folder
    return None


def is_wifi_folder(folder_path):
    return showing_folder(folder_path) == plugin.WIFI_FOLDER


def wifi_signature():
    """ What the Wi-Fi folder shows, so a change can be spotted """
    if not osmc_network.is_wifi_enabled():
        return ('off',)

    return tuple((n['path'], n['connected'], n['saved'], n['security'],
                  plugin.signal_level(n['strength']))
                 for n in plugin.visible_networks(osmc_network.wifi_services()))


def bluetooth_signature(osmc_bt):
    """ What the Bluetooth folder shows, so a change can be spotted """
    from .bluetooth_folder import devices, sort_devices

    if not osmc_bt.is_bluetooth_enabled():
        return ('off',)
    return tuple((d['address'], d['name'], d['connected'], d['paired'])
                 for d in sort_devices(devices(osmc_bt)))


def search_bluetooth_on_open():
    """ Network's setting: Search for devices when the list opens """
    try:
        return xbmcaddon.Addon(ADDON_ID).getSettingBool('bt_search_on_open')
    except Exception:
        return True


class Watcher(object):

    def __init__(self, osmc_bt=None):
        self.signature = None
        self.showing = None
        self.last_search = 0
        self._osmc_bt = osmc_bt

    @property
    def osmc_bt(self):
        if self._osmc_bt is None:
            from .bluetooth_folder import bluetooth
            self._osmc_bt = bluetooth()
        return self._osmc_bt

    def poll(self):
        showing = showing_folder(xbmc.getInfoLabel('Container.FolderPath'))

        if showing != self.showing:
            if self.showing == plugin.BLUETOOTH_FOLDER:
                self.stop_bluetooth_search()
            self.showing = showing
            self.signature = None

        if showing == plugin.WIFI_FOLDER:
            now = time.time()
            if now - self.last_search > SEARCH_INTERVAL and osmc_network.is_wifi_enabled():
                self.last_search = now
                osmc_network.scan_wifi()
            signature = wifi_signature()

        elif showing == plugin.BLUETOOTH_FOLDER:
            if search_bluetooth_on_open():
                self.keep_bluetooth_searching()
            signature = bluetooth_signature(self.osmc_bt)

        else:
            return

        if self.signature is not None and signature != self.signature:
            # leave the folder alone while a dialog (a password, a question) is open
            if xbmc.getCondVisibility('System.HasActiveModalDialog'):
                return
            log('%s changed, refreshing the folder' % showing)
            xbmc.executebuiltin('Container.Refresh')
        self.signature = signature

    def keep_bluetooth_searching(self):
        try:
            if self.osmc_bt.is_bluetooth_active() and not self.osmc_bt.is_discovering():
                self.osmc_bt.start_discovery()
        except Exception:
            log('Unable to start Bluetooth discovery')

    def stop_bluetooth_search(self):
        try:
            if self.osmc_bt.is_bluetooth_active() and self.osmc_bt.is_discovering():
                self.osmc_bt.stop_discovery()
        except Exception:
            log('Unable to stop Bluetooth discovery')
