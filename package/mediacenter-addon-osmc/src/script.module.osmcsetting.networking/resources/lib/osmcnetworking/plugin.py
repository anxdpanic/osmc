# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.networking

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    Network as a My OSMC plugin folder:
        ?module=osmcnetworking                     Wi-Fi, Bluetooth, Settings
        ?module=osmcnetworking&folder=wifi         the Wi-Fi networks
        ?module=osmcnetworking&wifi=<path>         connect to, or disconnect from, a network
        ?module=osmcnetworking&folder=bluetooth    the Bluetooth devices (bluetooth_folder.py)
        ?module=osmcnetworking&bt=<address>        pair, connect or disconnect a device
        ?module=osmcnetworking&action=<action>     wifi_on, wifi_off, search, other, forget,
                                                   bt_on, bt_off, bt_search, bt_remove,
                                                   settings (&category=<button id>)

    The settings service refreshes the Wi-Fi and Bluetooth folders while they show,
    and searches for devices while Bluetooth shows (see watcher.py).
"""

import os
from urllib.parse import urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger

from . import osmc_network

ADDON_ID = 'script.module.osmcsetting.networking'
MODULE_ID = 'osmcnetworking'
BASE_URL = 'plugin://service.osmc.settings/'
WIFI_FOLDER = 'wifi'
BLUETOOTH_FOLDER = 'bluetooth'

# the module's icon, the art for every item in these folders
ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'osmc', 'FO_Icon.png')

# Other network…: the security choices and connman's names for them
SECURITY_CHOICES = [('none', 32128), ('wep', 32129), ('psk', 32130), ('sae', 32131)]

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


def url(**params):
    params = dict(module=MODULE_ID, **params)
    return '%s?%s' % (BASE_URL, urlencode(params))


def wifi_folder_url():
    return url(folder=WIFI_FOLDER)


def settings_url(category):
    """ Network's add-on settings, on a category (Kodi numbers category buttons from -200) """
    return url(action='settings', category=category)


def wifi_settings_url():
    return settings_url(-199)  # Wireless


def bluetooth_settings_url():
    return settings_url(-198)  # Bluetooth


def signal_level(strength):
    """ The string id for a signal strength: Strong, Good or Weak """
    if strength > 60:
        return 32113
    if strength > 40:
        return 32114
    return 32115


def sort_networks(networks):
    """ Connected first, then saved, then by signal and name """
    return sorted(networks, key=lambda n: (not n['connected'], not n['saved'],
                                           -n['strength'], n['ssid'].lower()))


def visible_networks(services):
    """ The networks to list: named, not connman's hidden placeholders """
    return sort_networks([s for s in services if s['ssid'] and not s['hidden']])


class NetworkPlugin(object):

    def __init__(self, handle, params, addon=None):
        self.handle = handle
        self.params = params
        self.addon = addon or xbmcaddon.Addon(ADDON_ID)
        self.lang = LangRetriever(self.addon).lang
        self.dialog = xbmcgui.Dialog()
        self.url = url
        self.bluetooth_settings_url = bluetooth_settings_url
        self._bluetooth = None

    @property
    def bluetooth(self):
        if self._bluetooth is None:
            from .bluetooth_folder import BluetoothFolder
            self._bluetooth = BluetoothFolder(self)
        return self._bluetooth

    def run(self):
        if 'wifi' in self.params:
            self.select_network(self.params['wifi'])
        elif 'bt' in self.params:
            self.bluetooth.select_device(self.params['bt'])
        elif 'action' in self.params:
            self.do_action(self.params['action'])
        elif self.params.get('folder') == WIFI_FOLDER:
            self.list_wifi()
        elif self.params.get('folder') == BLUETOOTH_FOLDER:
            self.end_directory(self.bluetooth.list_items(), self.lang(32003))
        else:
            self.list_root()

    # ---- helpers -------------------------------------------------------------------------

    def label(self, name, *details):
        details = [d for d in details if d]
        if not details:
            return name
        return '%s  [LIGHT]•  %s[/LIGHT]' % (name, '  •  '.join(details))

    def end_directory(self, items, category):
        for _, list_item, _ in items:
            list_item.setArt({'icon': ICON, 'thumb': ICON})
        xbmcplugin.setPluginCategory(self.handle, category)
        xbmcplugin.addDirectoryItems(self.handle, items, len(items))
        xbmcplugin.endOfDirectory(self.handle, succeeded=True, cacheToDisc=False)

    @staticmethod
    def busy(show):
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)' if show
                            else 'Dialog.Close(busydialognocancel)')

    @staticmethod
    def refresh():
        xbmc.executebuiltin('Container.Refresh')

    def notify(self, message):
        self.dialog.notification(self.lang(32107), message)  # Wi-Fi

    # ---- Network folder ------------------------------------------------------------------

    def list_root(self):
        mysql_wait_for_network_check(self.lang)

        items = []
        if osmc_network.is_wifi_available():
            if not osmc_network.is_wifi_enabled():
                status = self.lang(32135)  # Off
            else:
                connected = next(iter(n for n in osmc_network.wifi_services() if n['connected']), None)
                status = self.lang(32108) % connected['ssid'] if connected else self.lang(32136)
            items.append((wifi_folder_url(),
                          xbmcgui.ListItem(self.label(self.lang(32107), status), offscreen=True),
                          True))

        if self.bluetooth.osmc_bt.is_bluetooth_available():
            items.append((url(folder=BLUETOOTH_FOLDER),
                          xbmcgui.ListItem(self.label(self.lang(32003), self.bluetooth.status()),
                                           offscreen=True),
                          True))

        # Network's add-on settings, on Wired
        wired = osmc_network.get_ethernet_settings() or {}
        wired_status = self.lang(32133) if wired.get('State') in ('ready', 'online') \
            else self.lang(32134)
        items.append((url(action='settings'),
                      xbmcgui.ListItem(self.label(self.lang(32132), wired_status), offscreen=True),
                      False))

        self.end_directory(items, self.addon_name())

    def addon_name(self):
        return xbmcaddon.Addon('service.osmc.settings').getLocalizedString(32052)  # Network

    # ---- Wi-Fi folder --------------------------------------------------------------------

    def context_menu(self, network=None):
        menu = []
        if network and network['saved']:
            menu.append((self.lang(32120), 'RunPlugin(%s)' % url(action='forget', path=network['path'])))
        menu.append((self.lang(32117), 'RunPlugin(%s)' % url(action='wifi_off')))
        menu.append((self.lang(32121), 'RunPlugin(%s)' % wifi_settings_url()))
        menu.append((self.lang(32118), 'RunPlugin(%s)' % url(action='search')))
        return menu

    def list_wifi(self):
        items = []

        if not osmc_network.is_wifi_enabled():
            list_item = xbmcgui.ListItem(self.lang(32116), offscreen=True)  # Turn on Wi-Fi
            list_item.addContextMenuItems([(self.lang(32121),
                                            'RunPlugin(%s)' % wifi_settings_url())])
            items.append((url(action='wifi_on'), list_item, False))
            self.end_directory(items, self.lang(32107))
            return

        networks = visible_networks(osmc_network.wifi_services())

        if not networks:
            list_item = xbmcgui.ListItem(self.lang(32118), offscreen=True)  # Search again
            list_item.addContextMenuItems(self.context_menu())
            items.append((url(action='search'), list_item, False))

        for network in networks:
            details = [
                self.lang(32109) if network['connected'] else
                (self.lang(32110) if network['saved'] else ''),  # Connected / Saved
                self.lang(32112) if network['security'] == 'none' else self.lang(32111),
                self.lang(signal_level(network['strength'])),
            ]
            list_item = xbmcgui.ListItem(self.label(network['ssid'], *details), offscreen=True)
            list_item.setProperty('ssid', network['ssid'])
            if network['connected']:
                list_item.select(True)  # skins draw it in their selected colour
            list_item.addContextMenuItems(self.context_menu(network))
            # a stable path per network, so focus stays put when the folder refreshes
            items.append((url(wifi=network['path']), list_item, False))

        list_item = xbmcgui.ListItem(self.lang(32119), offscreen=True)  # Other network…
        list_item.addContextMenuItems(self.context_menu())
        items.append((url(action='other'), list_item, False))

        self.end_directory(items, self.lang(32107))

    # ---- actions -------------------------------------------------------------------------

    def do_action(self, action):
        if action.startswith('bt_'):
            self.bluetooth.do_action(action, self.params)

        elif action == 'wifi_on':
            osmc_network.toggle_wifi_state(True)
            self.busy(True)
            try:
                osmc_network.scan_wifi()
            finally:
                self.busy(False)
            self.refresh()

        elif action == 'wifi_off':
            osmc_network.toggle_wifi_state(False)
            self.refresh()

        elif action == 'search':
            self.busy(True)
            try:
                osmc_network.scan_wifi()
            finally:
                self.busy(False)
            self.refresh()

        elif action == 'forget':
            osmc_network.wifi_remove(self.params.get('path', ''))
            self.refresh()

        elif action == 'other':
            self.other_network()

        elif action == 'settings':
            from .network_settings import open_settings
            category = self.params.get('category')
            open_settings(self.addon, self.lang, int(category) if category else None)
            self.refresh()

    def select_network(self, path):
        services = osmc_network.wifi_services()
        network = next(iter(s for s in services if s['path'] == path), None)
        if not network:
            self.refresh()
            return

        connected = next(iter(s for s in services if s['connected']), None)

        if network['connected']:
            if self.dialog.yesno(self.lang(32107), self.lang(32123) % network['ssid'],
                                 defaultbutton=xbmcgui.DLG_YESNO_NO_BTN):
                osmc_network.wifi_disconnect(path)
                self.refresh()
            return

        if connected and not self.dialog.yesno(
                self.lang(32107), self.lang(32122) % (connected['ssid'], network['ssid']),
                defaultbutton=xbmcgui.DLG_YESNO_NO_BTN):
            return

        self.connect(network['path'], network['ssid'], network['security'], network['saved'])

    def ask_password(self, ssid):
        return self.dialog.input(self.lang(32124) % ssid, type=xbmcgui.INPUT_ALPHANUM,
                                 option=xbmcgui.ALPHANUM_HIDE_INPUT)

    def connect(self, path, ssid, security, saved):
        secured = security != 'none'

        password = None
        if secured and not saved:
            password = self.ask_password(ssid)
            if not password:
                return

        lib_path = os.path.dirname(os.path.abspath(__file__)) + '/'
        self.busy(True)
        try:
            ok = osmc_network.wifi_connect(path, password, ssid, lib_path)
        finally:
            self.busy(False)

        if not ok and secured and saved and password is None:
            # the saved password no longer works
            password = self.ask_password(ssid)
            if password:
                self.busy(True)
                try:
                    ok = osmc_network.wifi_connect(path, password, ssid, lib_path)
                finally:
                    self.busy(False)

        self.notify((self.lang(32108) if ok else self.lang(32125)) % ssid)
        self.refresh()

    def other_network(self):
        ssid = self.dialog.input(self.lang(32126), type=xbmcgui.INPUT_ALPHANUM)
        if not ssid:
            return

        choice = self.dialog.select(self.lang(32127) % ssid,
                                    [self.lang(string_id) for _, string_id in SECURITY_CHOICES])
        if choice < 0:
            return
        security = SECURITY_CHOICES[choice][0]

        hidden = next(iter(s for s in osmc_network.wifi_services()
                           if s['hidden'] and s['security'] == security), None)
        if not hidden:
            log('No hidden %s network found for %s' % (security, ssid))
            self.notify(self.lang(32125) % ssid)
            return

        self.connect(hidden['path'], ssid, security, saved=False)


def mysql_wait_for_network_check(lang):
    """ With a remote MySQL server in advancedsettings.xml, turn on Wait for Network
        unless the user undoes it (today's yes/no, closing itself after 10 s) """
    from .osmc_advset_editor import AdvancedSettingsEditor

    editor = AdvancedSettingsEditor(log)
    advset_dict = editor.parse_advanced_settings()
    valid, _ = editor.validate_advset_dict(advset_dict, reject_empty=True, exclude_name=True)

    if not valid or not editor.server_not_localhost(advset_dict):
        return

    if osmc_network.is_connman_wait_for_network_enabled():
        return

    undo_change = xbmcgui.Dialog().yesno('MyOSMC', lang(32078),
                                         nolabel=lang(32080), yeslabel=lang(32079),
                                         autoclose=10000)
    if not undo_change:
        osmc_network.toggle_wait_for_network(True)


def run(handle, params):
    NetworkPlugin(handle, params).run()
