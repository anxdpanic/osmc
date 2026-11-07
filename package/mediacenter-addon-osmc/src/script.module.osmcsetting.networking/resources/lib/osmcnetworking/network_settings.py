# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.networking

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    Network's settings (Wired, Wireless, Bluetooth, Tethering, MySQL) in Kodi's add-on
    settings dialog. Before it opens, connman's live values and advancedsettings.xml's
    MySQL block are written into the settings; when it closes with OK, what changed is
    applied, so OK, Cancel and Defaults mean what they say.
"""

import os
import subprocess
import threading
import traceback

import xbmc
import xbmcgui
import xbmcvfs
from osmccommon.osmc_logging import StandardLogger

from . import osmc_network

ADDON_ID = 'script.module.osmcsetting.networking'
PROTOCOL = 'IPV4'

# category buttons in the add-on settings dialog (Kodi numbers them from -200)
WIRED = -200
WIRELESS = -199
BLUETOOTH = -198
TETHERING = -197
MYSQL = -196

WINDOW_DIALOG_ADDON_SETTINGS = 10140
NFS_REBOOT_FILE = '/tmp/.osmc_nfs_reboot_required'

DHCP = 0
MANUAL = 1

IP_KEYS = ['address', 'netmask', 'gateway', 'dns1', 'dns2']

MYSQL_KEYS = ['mysql_video', 'mysql_video_name', 'mysql_video_host', 'mysql_video_port',
              'mysql_video_user', 'mysql_video_pass', 'mysql_import_watched',
              'mysql_import_resume', 'mysql_music', 'mysql_music_name', 'mysql_music_host',
              'mysql_music_port', 'mysql_music_user', 'mysql_music_pass']

TETHERING_KEYS = ['hotspot_ssid', 'hotspot_passphrase', 'tethering_share', 'tethering_enabled']

BOOLS = {'wired_present', 'wired_enabled', 'wait_for_network', 'wireless_present',
         'bt_enabled', 'bt_search_on_open', 'tethering_enabled', 'mysql_video',
         'mysql_import_watched', 'mysql_import_resume', 'mysql_music'}
INTS = {'wired_method', 'wireless_method', 'tethering_share'}

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


# ---- reading and writing the add-on's settings ---------------------------------------------

def write_settings(addon, values):
    for key, value in values.items():
        if key in BOOLS:
            addon.setSettingBool(key, bool(value))
        elif key in INTS:
            addon.setSettingInt(key, int(value))
        else:
            addon.setSetting(key, '' if value is None else str(value))


def read_settings(addon, keys):
    values = {}
    for key in keys:
        if key in BOOLS:
            values[key] = addon.getSettingBool(key)
        elif key in INTS:
            values[key] = addon.getSettingInt(key)
        else:
            values[key] = addon.getSetting(key)
    return values


# ---- live values ---------------------------------------------------------------------------

def is_manual(config):
    return config.get(PROTOCOL, {}).get('Method', 'dhcp') in ('manual', 'nfs_manual')


def ip_values(prefix, config):
    ipv4 = config.get(PROTOCOL, {}) if config else {}
    nameservers = config.get('Nameservers', {}) if config else {}
    return {
        prefix + '_method': MANUAL if config and is_manual(config) else DHCP,
        prefix + '_address': ipv4.get('Address', ''),
        prefix + '_netmask': ipv4.get('Netmask', ''),
        prefix + '_gateway': ipv4.get('Gateway', ''),
        prefix + '_dns1': nameservers.get('DNS_1', ''),
        prefix + '_dns2': nameservers.get('DNS_2', ''),
    }


def status_text(lang, interface, state, name=None):
    if state in ('ready', 'online'):
        state_text = lang(32046) if state == 'online' else lang(32047)  # Connected / No internet
    elif state == 'configuration':
        state_text = lang(32076)  # configuring
    else:
        state_text = state
    return '  •  '.join([part for part in (interface, name, state_text) if part])


def live_values(lang):
    """ What the settings should show now """
    values = {}

    # wired
    wired_enabled = osmc_network.is_ethernet_enabled()
    wired = osmc_network.get_ethernet_settings() if wired_enabled else None
    values['wired_enabled'] = wired_enabled
    values['wired_present'] = bool(wired)
    values.update(ip_values('wired', wired))
    if not wired_enabled:
        values['wired_status'] = lang(32048)  # Disabled
    elif not wired:
        values['wired_status'] = lang(32049)  # No wired connection
    else:
        values['wired_status'] = status_text(lang, wired.get('Interface', ''), wired.get('State', ''))
    values['wait_for_network'] = osmc_network.is_connman_wait_for_network_enabled()

    # wireless
    wireless = {}
    try:
        if osmc_network.is_wifi_enabled():
            wireless = osmc_network.get_connected_wifi()
    except Exception:
        log(traceback.format_exc())
    values['wireless_present'] = bool(wireless)
    values.update(ip_values('wireless', wireless))
    values['wireless_status'] = status_text(lang, wireless.get('Interface', ''), wireless.get('State', ''),
                                            wireless.get('SSID')) if wireless else lang(32050)

    # bluetooth
    try:
        from .bluetooth_folder import bluetooth
        values['bt_enabled'] = bluetooth().is_bluetooth_enabled()
    except Exception:
        values['bt_enabled'] = False

    # tethering
    values['hotspot_ssid'] = osmc_network.get_tethering_ssid() or 'osmc_wifi'
    values['hotspot_passphrase'] = osmc_network.get_tethering_passphrase() or 'h0tsp0t0smc'
    tethering_ethernet = osmc_network.is_tethering_ethernet()
    values['tethering_share'] = 1 if tethering_ethernet else 0
    values['tethering_enabled'] = bool(tethering_ethernet or osmc_network.is_tethering_wifi())

    values.update(mysql_values(advanced_settings_editor().parse_advanced_settings()))
    return values


# ---- MySQL ---------------------------------------------------------------------------------

def advanced_settings_editor():
    from .osmc_advset_editor import AdvancedSettingsEditor
    return AdvancedSettingsEditor(log)


def mysql_values(advset_dict):
    main = (advset_dict or {}).get('advancedsettings', {}) or {}
    video = main.get('videodatabase', {}) or {}
    music = main.get('musicdatabase', {}) or {}
    library = main.get('videolibrary', {}) or {}
    return {
        'mysql_video': bool(video),
        'mysql_video_name': video.get('name', 'MyVideos'),
        'mysql_video_host': video.get('host', ''),
        'mysql_video_port': video.get('port', '3306'),
        'mysql_video_user': video.get('user', 'kodi'),
        'mysql_video_pass': video.get('pass', 'kodi'),
        'mysql_import_watched': library.get('importwatchedstate', 'true') == 'true',
        'mysql_import_resume': library.get('importresumepoint', 'true') == 'true',
        'mysql_music': bool(music),
        'mysql_music_name': music.get('name', 'MyMusic'),
        'mysql_music_host': music.get('host', ''),
        'mysql_music_port': music.get('port', '3306'),
        'mysql_music_user': music.get('user', 'kodi'),
        'mysql_music_pass': music.get('pass', 'kodi'),
    }


def mysql_dict(advset_dict, values):
    """ advancedsettings.xml's dictionary with the MySQL settings replaced """
    advset_dict = advset_dict or {}
    main = dict(advset_dict.get('advancedsettings', {}) or {})

    def database(prefix, default_name):
        return {
            'type': 'mysql',
            'name': values[prefix + '_name'] or default_name,
            'host': values[prefix + '_host'],
            'port': str(values[prefix + '_port'] or '3306'),
            'user': values[prefix + '_user'],
            'pass': values[prefix + '_pass'],
        }

    library = dict(main.get('videolibrary', {}) or {})
    if values['mysql_video']:
        main['videodatabase'] = database('mysql_video', 'MyVideos')
        for key, setting in (('importwatchedstate', 'mysql_import_watched'),
                             ('importresumepoint', 'mysql_import_resume')):
            if values[setting]:
                library[key] = 'true'
            else:
                library.pop(key, None)
    else:
        main.pop('videodatabase', None)
        library.pop('importwatchedstate', None)
        library.pop('importresumepoint', None)

    if library:
        main['videolibrary'] = library
    else:
        main.pop('videolibrary', None)

    if values['mysql_music']:
        main['musicdatabase'] = database('mysql_music', 'MyMusic')
    else:
        main.pop('musicdatabase', None)

    return {'advancedsettings': main}


# ---- the dialog ----------------------------------------------------------------------------

class NetworkSettings(object):

    def __init__(self, addon, lang, dialog=None):
        self.addon = addon
        self.lang = lang
        self.dialog = dialog or xbmcgui.Dialog()

    @staticmethod
    def focus_category(category):
        """ Moves focus to a category once the settings dialog is showing """
        def _focus():
            monitor = xbmc.Monitor()
            for _ in range(50):
                if xbmcgui.getCurrentWindowDialogId() == WINDOW_DIALOG_ADDON_SETTINGS:
                    xbmc.executebuiltin('SetFocus(%d)' % category)
                    return
                if monitor.waitForAbort(0.1):
                    return
        threading.Thread(target=_focus, daemon=True).start()

    def open(self, category=None):
        live = live_values(self.lang)
        write_settings(self.addon, live)
        keys = list(live.keys()) + ['bt_search_on_open']
        # compare against what the settings hold (None reads back as ''), not the live values
        before = read_settings(self.addon, keys)

        while True:
            if category is not None:
                self.focus_category(category)
            self.addon.openSettings()

            after = read_settings(self.addon, keys)
            if after == before:
                return  # Cancel, or nothing changed

            category = self.apply(before, after)
            if category is None:
                return
            # a check failed: reopen on that category with the user's values kept

    # -- applying --

    def apply(self, before, after):
        """ Applies what changed; returns a category to reopen on, or None """
        changed = {key for key in after if after[key] != before.get(key)}
        log('Network settings changed: %s' % sorted(changed))

        if changed & set(TETHERING_KEYS):
            reopen = self.check_tethering(after)
            if reopen is not None:
                return reopen

        if changed & set(MYSQL_KEYS):
            reopen = self.apply_mysql(after)
            if reopen is not None:
                return reopen

        if 'wired_enabled' in changed:
            osmc_network.toggle_ethernet_state(after['wired_enabled'])

        nfs = False
        if after['wired_present'] and changed & {'wired_' + k for k in ['method'] + IP_KEYS}:
            nfs = self.apply_addresses('wired', osmc_network.get_ethernet_settings(), after)

        if after['wireless_present'] and changed & {'wireless_' + k for k in ['method'] + IP_KEYS}:
            self.apply_addresses('wireless', osmc_network.get_connected_wifi(), after)

        if 'wait_for_network' in changed:
            osmc_network.toggle_wait_for_network(after['wait_for_network'])

        if 'bt_enabled' in changed:
            from .bluetooth_folder import bluetooth
            bluetooth().toggle_bluetooth_state(after['bt_enabled'])

        if changed & set(TETHERING_KEYS):
            self.apply_tethering(before, after)

        if nfs:
            with open(NFS_REBOOT_FILE, 'w', encoding='utf-8') as open_file:
                open_file.write('d')
            # 'NFS Network Settings' 'Your Settings will not take effect until you reboot. Reboot Now?'
            if self.dialog.yesno(self.lang(32036), self.lang(32037)):
                xbmc.executebuiltin('Reboot')

        return None

    @staticmethod
    def apply_addresses(prefix, config, values):
        """ Applies DHCP or manual addresses to a connman service; True for NFS """
        if not config:
            return False

        nfs = config.get(PROTOCOL, {}).get('Method', '').startswith('nfs')
        manual = values[prefix + '_method'] == MANUAL

        ipv4 = config.setdefault(PROTOCOL, {})
        if nfs:
            ipv4['Method'] = 'nfs_manual' if manual else 'nfs_dhcp'
        else:
            ipv4['Method'] = 'manual' if manual else 'dhcp'

        if manual:
            ipv4['Address'] = values[prefix + '_address']
            ipv4['Netmask'] = values[prefix + '_netmask']
            ipv4['Gateway'] = values[prefix + '_gateway']
            nameservers = config.setdefault('Nameservers', {})
            nameservers['DNS_1'] = values[prefix + '_dns1']
            if values[prefix + '_dns2']:
                nameservers['DNS_2'] = values[prefix + '_dns2']
            else:
                nameservers.pop('DNS_2', None)

        log('Applying %s settings: %s' % (prefix, ipv4))
        osmc_network.apply_network_changes(config, PROTOCOL)
        return nfs

    def check_tethering(self, values):
        """ Today's checks before a Wi-Fi hotspot starts """
        if not values['tethering_enabled'] or values['tethering_share'] != 0:
            return None
        if not values['hotspot_ssid']:
            message = self.lang(32070)  # SSID must be set to enable WiFi Tethering
        elif len(values['hotspot_passphrase']) > 63:
            message = self.lang(32074)  # Passphrase must be 63 characters or less
        elif len(values['hotspot_passphrase']) < 8:
            message = self.lang(32071)  # Passphrase must at least 8 characters long
        else:
            return None
        _ = self.dialog.ok(self.lang(32063), message)  # Portable Hotspot
        return TETHERING

    def apply_tethering(self, before, after):
        if before['tethering_enabled']:
            osmc_network.tethering_disable()
        if not after['tethering_enabled']:
            return

        if after['tethering_share'] == 0:
            ok = osmc_network.tethering_enable('wifi', after['hotspot_ssid'], after['hotspot_passphrase'])
        else:
            ok = osmc_network.tethering_enable('ethernet', None, None)

        if not ok:
            # 'Portable Hotspot' 'Error enabling hotspot - see log for details'
            _ = self.dialog.ok(self.lang(32063), self.lang(32072))

    def apply_mysql(self, values):
        editor = advanced_settings_editor()
        advset_dict = mysql_dict(editor.parse_advanced_settings(), values)

        valid, invalidity = editor.validate_advset_dict(advset_dict, no_pw_ok=True)
        if not valid and invalidity == 'missing mysql':
            # 'MySQL settings are incomplete.' 'Discard MySQL settings changes?'
            if self.dialog.yesno(self.lang(32081), '[CR]'.join([self.lang(32082), self.lang(32083)])):
                return None
            return MYSQL

        location = os.path.join(xbmcvfs.translatePath('special://userdata'), 'advancedsettings.xml')
        try:
            editor.write_advancedsettings(location, advset_dict)
        except IOError:
            log('IOError writing advancedsettings.xml, trying to fix its permissions')
            if subprocess.call(['sudo', 'chmod', '666', location]) == 0:
                try:
                    editor.write_advancedsettings(location, advset_dict)
                except Exception:
                    log(traceback.format_exc())
                    _ = self.dialog.ok(self.lang(32081), '[CR]'.join([self.lang(32088), self.lang(32087)]))
            else:
                _ = self.dialog.ok(self.lang(32081), '[CR]'.join([self.lang(32089), self.lang(32087)]))

        # a remote MySQL server needs the network at boot
        if editor.server_not_localhost(advset_dict) and \
                editor.validate_advset_dict(advset_dict, reject_empty=True)[0]:
            osmc_network.toggle_wait_for_network(True)

        return None


def open_settings(addon, lang, category=None):
    NetworkSettings(addon, lang).open(category)
