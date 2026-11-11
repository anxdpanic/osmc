# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.osmc.setup

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    The Network step: Wi-Fi with My OSMC's rules (osmcnetworking.plugin), and the wired
    settings in place.
"""

import copy
import ipaddress
import os
import traceback

import xbmcaddon
import xbmcgui
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger

ADDON_ID = 'script.osmc.setup'
NETWORKING_ID = 'script.module.osmcsetting.networking'

# the wired rows, in order: (key, string id, where the value lives in osmc_network's settings)
WIRED_ROWS = [
    ('Address', 32138, ('IPV4', 'Address')),
    ('Netmask', 32139, ('IPV4', 'Netmask')),
    ('Gateway', 32140, ('IPV4', 'Gateway')),
    ('DNS_1', 32141, ('Nameservers', 'DNS_1')),
    ('DNS_2', 32142, ('Nameservers', 'DNS_2')),
]

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


def network():
    """ osmc_network, imported late as it needs dbus """
    from osmcnetworking import osmc_network
    return osmc_network


def is_ip_address(value):
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def wired_value(settings, where):
    section, key = where
    return (settings.get(section) or {}).get(key) or ''


class NetworkStep(object):

    def __init__(self, lang, refreshed):
        """ lang: setup's strings; refreshed: called when a Wi-Fi change is done """
        self.lang = lang
        self.refreshed = refreshed
        self.net_lang = LangRetriever(xbmcaddon.Addon(NETWORKING_ID)).lang
        self._plugin = None
        self.wired = None  # the wired settings being edited

    @property
    def plugin(self):
        """ My OSMC's Wi-Fi folder, used here for its connect and Other network… dialogs """
        if self._plugin is None:
            from osmcnetworking.plugin import NetworkPlugin
            self._plugin = NetworkPlugin(handle=-1, params={})
            self._plugin.refresh = self.refreshed
        return self._plugin

    # ---- the step's rows -----------------------------------------------------------------

    def status(self):
        """ (help text, Wi-Fi value, wired value, connection, online) """
        osmc_network = network()

        wifi_value = self.lang(32134)  # Not in use
        ssid = None
        try:
            if not osmc_network.is_wifi_available():
                wifi_value = ''
            elif not osmc_network.is_wifi_enabled():
                wifi_value = self.lang(32144)  # Off
            else:
                connected = next(iter(n for n in osmc_network.wifi_services()
                                      if n['connected']), None)
                if connected:
                    ssid = connected['ssid']
                    wifi_value = ssid
                else:
                    wifi_value = self.lang(32132)  # Not connected
        except Exception:
            log(traceback.format_exc())

        wired = None
        try:
            wired = osmc_network.get_ethernet_settings()
        except Exception:
            log(traceback.format_exc())

        cabled = bool(wired and wired.get('State') in ('ready', 'online'))
        if cabled:
            wired_value = self.lang(32131)  # Connected
        elif wired:
            wired_value = self.lang(32132)  # Not connected
        else:
            wired_value = self.lang(32133)  # No cable

        online = False
        try:
            online = osmc_network.has_network_connection(True)
        except Exception:
            log(traceback.format_exc())

        if cabled:
            help_text = self.lang(32125)  # connected by cable
            connection = ('wired', None)
        elif ssid:
            help_text = self.lang(32124) % ssid  # connected to <ssid> by Wi-Fi
            connection = ('wifi', ssid)
        else:
            help_text = self.lang(32126)  # not connected
            connection = (None, None)

        return help_text, wifi_value, wired_value, connection, online

    # ---- Wi-Fi list ----------------------------------------------------------------------

    def wifi_items(self):
        """ The Wi-Fi list in place: [(label, key), ...] """
        osmc_network = network()
        from osmcnetworking.plugin import signal_level, visible_networks

        if not osmc_network.is_wifi_enabled():
            return [(self.net_lang(32116), 'wifi_on')]  # Turn on Wi-Fi

        items = []
        networks = visible_networks(osmc_network.wifi_services())
        for wifi in networks:
            details = [
                self.net_lang(32109) if wifi['connected'] else
                (self.net_lang(32110) if wifi['saved'] else ''),  # Connected / Saved
                self.net_lang(32112) if wifi['security'] == 'none' else self.net_lang(32111),
                self.net_lang(signal_level(wifi['strength'])),
            ]
            items.append((self.plugin.label(wifi['ssid'], *details), wifi['path']))

        if not networks:
            items.append((self.net_lang(32118), 'search'))  # Search again
        items.append((self.net_lang(32119), 'other'))  # Other network…
        return items

    def choose_wifi(self, key):
        osmc_network = network()
        if key == 'wifi_on':
            osmc_network.toggle_wifi_state(True)
            self.scan()
        elif key == 'search':
            self.scan()
        elif key == 'other':
            self.plugin.other_network()
        else:
            self.plugin.select_network(key)

    def scan(self):
        self.plugin.busy(True)
        try:
            network().scan_wifi()
        except Exception:
            log(traceback.format_exc())
        finally:
            self.plugin.busy(False)
        self.refreshed()

    # ---- wired settings ------------------------------------------------------------------

    def open_wired(self):
        """ Starts editing the wired settings; False when there is no wired connection """
        try:
            settings = network().get_ethernet_settings()
        except Exception:
            log(traceback.format_exc())
            settings = None
        if not settings or 'IPV4' not in settings:
            return False
        self.wired = copy.deepcopy(settings)
        self.original_wired = copy.deepcopy(settings)
        return True

    def is_manual(self):
        return self.wired['IPV4'].get('Method') in ('manual', 'nfs_manual')

    def wired_rows(self):
        """ [(key, label, value, enabled), ...]; the addresses are read-only on DHCP """
        manual = self.is_manual()
        rows = [('Method', self.lang(32135), self.lang(32137) if manual else self.lang(32136), True)]
        for key, string_id, where in WIRED_ROWS:
            rows.append((key, self.lang(string_id), wired_value(self.wired, where), manual))
        return rows

    def edit_wired(self, key):
        if key == 'Method':
            nfs = self.wired['IPV4'].get('Method', '').startswith('nfs_')
            if self.is_manual():
                self.wired['IPV4']['Method'] = 'nfs_dhcp' if nfs else 'dhcp'
            else:
                self.wired['IPV4']['Method'] = 'nfs_manual' if nfs else 'manual'
            return

        if not self.is_manual():
            return

        where = next(iter(w for k, _, w in WIRED_ROWS if k == key))
        label = next(iter(self.lang(s) for k, s, _ in WIRED_ROWS if k == key))
        value = xbmcgui.Dialog().input(label, wired_value(self.wired, where),
                                       type=xbmcgui.INPUT_IPADDRESS)
        if not value:
            return
        if not is_ip_address(value):
            xbmcgui.Dialog().notification(label, self.lang(32153))  # Not a valid IP address
            return
        section, field = where
        self.wired.setdefault(section, {})[field] = value

    def apply_wired(self):
        """ Applies the wired settings, if they changed """
        changed = self.wired != self.original_wired
        if changed:
            self.plugin.busy(True)
            try:
                network().apply_network_changes(self.wired, 'IPV4')
            except Exception:
                log(traceback.format_exc())
            finally:
                self.plugin.busy(False)
        self.wired = None
        return changed
