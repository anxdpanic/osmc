# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.osmc.setup

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    What setup reads from, and changes on, Kodi and the device.
"""

import json
import os
import socket
import subprocess
import traceback
from contextlib import closing

import xbmc
from osmccommon.osmc_logging import StandardLogger

ADDON_ID = 'script.osmc.setup'

# the first-run flag the settings service checks
COMPLETED_FLAG = '/walkthrough_completed'

# looked up once, when Timezone is first shown and the device is online
TIMEZONE_LOOKUP_URL = 'http://ip-api.com/json/?fields=status,country,timezone'

NEWSLETTER_URL = 'https://osmc.tv/osmc/api/newsletter/?p=subscribe&id=1'

UPDATE_SOCKET = '/var/tmp/osmc.settings.update.sockfile'

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


# ---- Kodi ----------------------------------------------------------------------------------

def jsonrpc(method, params=None):
    request = {'jsonrpc': '2.0', 'id': 1, 'method': method}
    if params is not None:
        request['params'] = params
    response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if 'error' in response:
        log('%s failed: %s' % (method, response['error']))
    return response.get('result')


def regional_settings():
    """ Kodi's regional settings by id, each with value and options [(label, value), ...] """
    result = jsonrpc('Settings.GetSettings',
                     {'filter': {'section': 'interface', 'category': 'regional'}}) or {}
    settings = {}
    for setting in result.get('settings', []):
        settings[setting['id']] = {
            'value': setting.get('value'),
            'options': [(o['label'], o['value']) for o in setting.get('options') or []],
        }
    return settings


def regional_setting(setting_id):
    return regional_settings().get(setting_id, {'value': '', 'options': []})


def label_of(setting, value=None):
    """ The label Kodi shows for a setting's value """
    value = setting['value'] if value is None else value
    return next(iter(label for label, v in setting['options'] if v == value), value or '')


def set_setting(setting_id, value):
    return jsonrpc('Settings.SetSettingValue', {'setting': setting_id, 'value': value})


def languages():
    """ The installed interface languages [(name, add-on id), ...], named as in Kodi's list """
    result = jsonrpc('Addons.GetAddons', {'type': 'kodi.resource.language',
                                          'properties': ['name']}) or {}
    found = [(a['name'], a['addonid']) for a in result.get('addons', [])]
    return sorted(found, key=lambda language: language[0].lower())


def current_language():
    """ (name, add-on id) of the interface language, named as in Kodi's language list """
    addon_id = regional_setting('locale.language')['value']
    name = next(iter(n for n, a in languages() if a == addon_id), None)
    return name or xbmc.getInfoLabel('System.Language'), addon_id


def set_language(addon_id):
    """ Kodi reloads its interface; the setup window reopens afterwards """
    xbmc.executebuiltin('SetGUILanguage(%s)' % addon_id)


def set_timezone(country, timezone):
    set_setting('locale.timezonecountry', country)
    if timezone:
        set_setting('locale.timezone', timezone)
        try:
            xbmc.settimezone(timezone)  # OSMC's Kodi sets the system's timezone too
        except Exception:
            log(traceback.format_exc())


def timezones(country):
    """ Kodi offers the timezones of the current timezone country """
    set_setting('locale.timezonecountry', country)
    setting = regional_setting('locale.timezone')
    return setting['options'], setting['value']


def detect_timezone(country_options):
    """ (country, timezone) from the connection's location, or (None, None) """
    try:
        import requests
        found = requests.get(TIMEZONE_LOOKUP_URL, timeout=5).json()
    except Exception:
        log('Timezone lookup failed')
        return None, None

    if found.get('status') != 'success':
        return None, None

    country = found.get('country')
    if country not in [value for _, value in country_options]:
        log('Unknown timezone country %s' % country)
        return None, None
    return country, found.get('timezone')


# ---- device --------------------------------------------------------------------------------

def is_vero():
    try:
        with open('/proc/cmdline', 'r', encoding='utf-8') as cmdline:
            for part in cmdline.read().split():
                if part.startswith('osmcdev=') and part.split('=', 1)[1].startswith('vero'):
                    return True
    except Exception:
        pass
    return False


def is_remote_paired():
    """ The OSMC remote shows as an input device once it is paired """
    try:
        with open('/proc/bus/input/devices', 'r', encoding='utf-8') as devices:
            return 'OSMC Remote Controller' in devices.read()
    except Exception:
        return False


def hostname():
    try:
        return socket.gethostname()
    except Exception:
        return 'osmc'


def set_hostname(name):
    try:
        xbmc.sethostname(name)  # OSMC's Kodi
    except Exception:
        log(traceback.format_exc())


def is_ssh_enabled():
    return subprocess.call(['systemctl', 'is-enabled', '--quiet', 'ssh']) == 0


def set_ssh(enabled):
    action = ['enable', 'start'] if enabled else ['disable', 'stop']
    for verb in action:
        subprocess.call(['sudo', 'systemctl', verb, 'ssh'])


def set_password(password):
    """ The osmc user's password, which SSH uses """
    try:
        process = subprocess.Popen(['sudo', 'chpasswd'], stdin=subprocess.PIPE)
        process.communicate(('osmc:%s\n' % password).encode('utf-8'))
        return process.returncode == 0
    except Exception:
        log(traceback.format_exc())
        return False


def subscribe_newsletter(email):
    try:
        import requests
        requests.post(NEWSLETTER_URL, timeout=10, data={
            'email': email,
            'subscribe': 'subscribe',
            'list[7]': 'signup',
            'listname[7]': 'Device',
        })
    except Exception:
        log(traceback.format_exc())


def mark_done():
    """ The settings service skips setup from now on, and Kodi knows OSMC is ready """
    try:
        with open('/tmp/walkthrough_completed', 'w+', encoding='utf-8'):
            pass
        subprocess.call(['sudo', 'mv', '/tmp/walkthrough_completed', COMPLETED_FLAG])
        subprocess.call(['sudo', 'rm', '-f', '/tmp/NO_UPDATE'])
    except Exception:
        log(traceback.format_exc())

    try:
        xbmc.setosmcwalkthroughstatus(2)
    except Exception:
        log(traceback.format_exc())

    import xbmcgui
    xbmcgui.Window(10000).clearProperty('walkthrough_is_running')


def request_update_check():
    """ The updates service checks now, as Check for updates did after the old walkthrough """
    message = json.dumps(('settings_command', {'action': 'update'})).encode('utf-8')
    try:
        with closing(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)) as update_socket:
            update_socket.connect(UPDATE_SOCKET)
            update_socket.sendall(message)
    except Exception:
        log(traceback.format_exc())
