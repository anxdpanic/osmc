# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.networking

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    The Bluetooth folder in My OSMC's Network folder, with the same rules as Wi-Fi:
    devices only, connected first, then paired, then available; a search runs while
    the folder shows (see watcher.py).
"""

import os

import xbmcgui
from osmccommon.osmc_logging import StandardLogger

ADDON_ID = 'script.module.osmcsetting.networking'

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


def bluetooth():
    """ The Bluetooth helper; imported late as it needs dbus """
    from .osmc_bluetooth import OSMCBluetooth
    return OSMCBluetooth()


def is_audio(device):
    """ Audio devices replace each other; controllers, keyboards and remotes do not """
    return str(device.get('Icon', '')).startswith('audio')


def devices(osmc_bt):
    """ The devices BlueZ knows, as dicts: address, name, connected, paired, audio """
    found = []
    for address, properties in osmc_bt.list_devices().items():
        found.append({
            'address': str(address),
            'name': str(properties.get('Alias') or properties.get('Name') or address),
            'connected': bool(properties.get('Connected', False)),
            'paired': bool(properties.get('Paired', False)),
            'audio': is_audio(properties),
        })
    return found


def sort_devices(found):
    """ Connected first, then paired, then available, each by name """
    return sorted(found, key=lambda d: (not d['connected'], not d['paired'], d['name'].lower()))


class BluetoothFolder(object):
    """ Used by plugin.NetworkPlugin, whose helpers (label, url, refresh, ...) it shares """

    def __init__(self, plugin, osmc_bt=None):
        self.plugin = plugin
        self.lang = plugin.lang
        self.dialog = plugin.dialog
        self.osmc_bt = osmc_bt or bluetooth()

    def notify(self, message):
        self.dialog.notification(self.lang(32003), message)  # Bluetooth

    def status(self):
        """ The Bluetooth item's status in the Network folder """
        if not self.osmc_bt.is_bluetooth_enabled():
            return self.lang(32135)  # Off
        connected = [d for d in devices(self.osmc_bt) if d['connected']]
        if not connected:
            return self.lang(32136)  # Not connected
        if len(connected) == 1:
            return self.lang(32143)  # 1 device connected
        return self.lang(32142) % len(connected)

    def context_menu(self, device=None):
        url = self.plugin.url
        menu = []
        if device and device['paired']:
            menu.append((self.lang(32021), 'RunPlugin(%s)' % url(action='bt_remove', address=device['address'])))
        menu.append((self.lang(32138), 'RunPlugin(%s)' % url(action='bt_off')))
        menu.append((self.lang(32139), 'RunPlugin(%s)' % self.plugin.bluetooth_settings_url()))
        menu.append((self.lang(32118), 'RunPlugin(%s)' % url(action='bt_search')))
        return menu

    def list_items(self):
        url = self.plugin.url
        items = []

        if not self.osmc_bt.is_bluetooth_enabled():
            list_item = xbmcgui.ListItem(self.lang(32137), offscreen=True)  # Turn on Bluetooth
            list_item.addContextMenuItems([(self.lang(32139),
                                            'RunPlugin(%s)' % self.plugin.bluetooth_settings_url())])
            items.append((url(action='bt_on'), list_item, False))
            return items

        found = sort_devices(devices(self.osmc_bt))
        if not found:
            list_item = xbmcgui.ListItem(self.lang(32118), offscreen=True)  # Search again
            list_item.addContextMenuItems(self.context_menu())
            items.append((url(action='bt_search'), list_item, False))
            return items

        for device in found:
            state = self.lang(32109) if device['connected'] else \
                (self.lang(32140) if device['paired'] else self.lang(32141))
            list_item = xbmcgui.ListItem(self.plugin.label(device['name'], state), offscreen=True)
            if device['connected']:
                list_item.select(True)
            list_item.addContextMenuItems(self.context_menu(device))
            items.append((url(bt=device['address']), list_item, False))

        return items

    def do_action(self, action, params):
        if action == 'bt_on':
            self.osmc_bt.toggle_bluetooth_state(True)
        elif action == 'bt_off':
            self.osmc_bt.toggle_bluetooth_state(False)
        elif action == 'bt_search':
            try:
                self.osmc_bt.start_discovery()
            except Exception:
                log('Unable to start discovery')
        elif action == 'bt_remove':
            self.osmc_bt.remove_device(params.get('address', ''))
        self.plugin.refresh()

    def select_device(self, address):
        found = devices(self.osmc_bt)
        device = next(iter(d for d in found if d['address'] == address), None)
        if not device:
            self.plugin.refresh()
            return

        if device['connected']:
            if self.dialog.yesno(self.lang(32003), self.lang(32123) % device['name'],
                                 defaultbutton=xbmcgui.DLG_YESNO_NO_BTN):
                self.osmc_bt.disconnect_device(address)
                self.plugin.refresh()
            return

        # only an audio device replaces another; everything else connects alongside
        replaced = next(iter(d for d in found if d['connected'] and d['audio'] and device['audio']), None)
        if replaced:
            if not self.dialog.yesno(self.lang(32003),
                                     self.lang(32122) % (replaced['name'], device['name']),
                                     defaultbutton=xbmcgui.DLG_YESNO_NO_BTN):
                return
            self.osmc_bt.disconnect_device(replaced['address'])

        ok = True
        if not device['paired']:
            # the pairing agent asks for a passkey or PIN, or shows one, as the device needs
            ok = self.osmc_bt.pair_device(address)

        if ok:
            self.plugin.busy(True)
            try:
                ok = self.osmc_bt.connect_device(address)
            finally:
                self.plugin.busy(False)

        self.notify((self.lang(32108) if ok else self.lang(32125)) % device['name'])
        self.plugin.refresh()
