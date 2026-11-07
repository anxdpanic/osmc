# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of service.osmc.settings

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    My OSMC as a plugin folder: plugin://service.osmc.settings/
    One item per module; selecting one asks the settings service to open it.
"""

import os
import socket
import subprocess
import sys
from io import open
from urllib.parse import parse_qsl
from urllib.parse import urlencode

import xbmcaddon
import xbmcgui
import xbmcplugin
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger

ADDON_ID = 'service.osmc.settings'
BASE_URL = 'plugin://%s/' % ADDON_ID
SOCKET_FILE = '/var/tmp/osmc.settings.sockfile'
END_OF_LIFE_FILE = '/end_of_life_message'

PROPERTY_PREFIX = 'MyOSMC.Module'

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


class Plugin(object):

    def __init__(self, argv):
        self.base_url = argv[0]
        try:
            self.handle = int(argv[1])
        except (IndexError, ValueError):
            self.handle = -1
        query = argv[2][1:] if len(argv) > 2 and argv[2].startswith('?') else ''
        self.params = dict(parse_qsl(query))

        self.addon = xbmcaddon.Addon(ADDON_ID)
        self.lang = LangRetriever(self.addon).lang
        self.window = xbmcgui.Window(10000)

    def run(self):
        module_id = self.params.get('module')
        if module_id:
            self.open_module(module_id)
            return

        self.list_modules()

    @staticmethod
    def send(message):
        """ Sends a message to the settings service, returns False if it does not answer """
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as open_socket:
                open_socket.connect(SOCKET_FILE)
                open_socket.sendall(message.encode('utf-8'))
        except Exception:
            log('My OSMC service did not answer: %s' % message)
            return False
        return True

    def service_unavailable(self):
        _ = xbmcgui.Dialog().ok(self.lang(32047), '[CR]'.join([self.lang(32007), self.lang(32005)]))

    def end_of_life_message(self):
        """ On a device OSMC no longer supports, the first opening says so, once """
        if not os.path.isfile(END_OF_LIFE_FILE):
            return

        with open(END_OF_LIFE_FILE, 'r', encoding='utf-8') as file_handle:
            eol_read = file_handle.readline(1)

        if eol_read == '1':
            return

        _ = xbmcgui.Dialog().ok(self.lang(32083), self.lang(32084))

        with open('/tmp/end_of_life_message', 'w', encoding='utf-8') as file_handle:
            file_handle.write('1')
            log('/tmp/end_of_life_message written')

        subprocess.call(['sudo', 'mv', '/tmp/end_of_life_message', END_OF_LIFE_FILE])

    def modules(self):
        """ The live modules, as published to the Home window by the settings service """
        try:
            count = int(self.window.getProperty('%s.Count' % PROPERTY_PREFIX))
        except ValueError:
            count = 0

        for index in range(count):
            prefix = '%s.%s' % (PROPERTY_PREFIX, index)
            module_id = self.window.getProperty('%s.id' % prefix)
            if not module_id:
                continue

            yield {
                'id': module_id,
                'label': self.window.getProperty('%s.label' % prefix),
                'description': self.window.getProperty('%s.description' % prefix),
                'icon': self.window.getProperty('%s.icon' % prefix),
            }

    def list_modules(self):
        modules = list(self.modules())
        if not modules or not self.send('ping'):
            self.service_unavailable()
            xbmcplugin.endOfDirectory(self.handle, succeeded=False)
            return

        self.end_of_life_message()

        items = []
        for module in modules:
            list_item = xbmcgui.ListItem(label=module['label'], offscreen=True)
            list_item.setArt({
                'icon': module['icon'],
                'thumb': module['icon'],
            })
            list_item.setProperty('description', module['description'])
            list_item.getVideoInfoTag().setPlot(module['description'])

            url = '%s?%s' % (BASE_URL, urlencode({'module': module['id']}))
            items.append((url, list_item, False))

        xbmcplugin.addDirectoryItems(self.handle, items, len(items))
        xbmcplugin.endOfDirectory(self.handle, succeeded=True, cacheToDisc=False)

    def open_module(self, module_id):
        if not self.send(module_id):
            self.service_unavailable()


def run(argv=None):
    Plugin(argv or sys.argv).run()
