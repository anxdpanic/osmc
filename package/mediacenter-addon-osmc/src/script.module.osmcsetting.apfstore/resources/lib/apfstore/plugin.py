# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.apfstore

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    The App Store as a My OSMC plugin folder:
        plugin://service.osmc.settings/?module=apfstore           the apps
        plugin://service.osmc.settings/?module=apfstore&app=<id>  one app's dialog

    Each confirmed Install or Uninstall goes straight to the update service,
    which shows its progress and result dialogs and refreshes this folder.
"""

import json
import os
import socket
from contextlib import closing
from urllib.parse import urlencode

import xbmcaddon
import xbmcgui
import xbmcplugin
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger

from . import store

ADDON_ID = 'script.module.osmcsetting.apfstore'
MODULE_ID = 'apfstore'
BASE_URL = 'plugin://service.osmc.settings/'
UPDATE_SOCKET = '/var/tmp/osmc.settings.update.sockfile'

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log

# Dialog().yesnocustom return values
CANCELLED = -1
NO = 0
YES = 1
CUSTOM = 2


def send_to_update_service(action, notification_heading, notification):
    message = json.dumps(('action_list', {
        'action': action,
        'notification_heading': notification_heading,
        'notification': notification,
    })).encode('utf-8')

    with closing(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)) as open_socket:
        open_socket.connect(UPDATE_SOCKET)
        open_socket.sendall(message)


class AppStorePlugin(object):

    def __init__(self, handle, params, addon=None):
        self.handle = handle
        self.params = params
        self.addon = addon or xbmcaddon.Addon(ADDON_ID)
        self.lang = LangRetriever(self.addon).lang
        self.dialog = xbmcgui.Dialog()
        self.store = store.Store(self.addon)

    def run(self):
        app_id = self.params.get('app')
        if app_id:
            self.app_dialog(app_id)
        else:
            self.list_apps()

    def unsupported(self):
        if store.is_unsupported_alpha():
            _ = self.dialog.ok(self.lang(32017), '[CR]'.join([self.lang(32018), self.lang(32019)]))
            return True
        return False

    def label(self, app):
        if app.installed:
            return '%s  [LIGHT]•  %s[/LIGHT]' % (app.name, self.lang(32005))
        return app.name

    def list_apps(self):
        if self.unsupported():
            xbmcplugin.endOfDirectory(self.handle, succeeded=False)
            return

        apps = self.store.apps()
        if apps is None:
            _ = self.dialog.ok(self.lang(32025), self.lang(32028))  # App Store / cannot reach
            xbmcplugin.endOfDirectory(self.handle, succeeded=False)
            return

        items = []
        for app in apps:
            list_item = xbmcgui.ListItem(label=self.label(app), offscreen=True)
            list_item.setArt({'icon': app.icon, 'thumb': app.icon})
            list_item.getVideoInfoTag().setPlot(app.shortdesc)
            list_item.setProperty('description', app.shortdesc)
            url = '%s?%s' % (BASE_URL, urlencode({'module': MODULE_ID, 'app': app.id}))
            items.append((url, list_item, False))

        xbmcplugin.setPluginCategory(self.handle, self.lang(32025))  # Container.FolderName
        xbmcplugin.addDirectoryItems(self.handle, items, len(items))
        xbmcplugin.endOfDirectory(self.handle, succeeded=True, cacheToDisc=False)

    def details(self, app):
        facts = '  •  '.join([
            '%s %s' % (self.lang(32014), app.version),
            '%s: %s' % (self.lang(32013), app.maintainedby),
            '%s: %s' % (self.lang(32012), app.lastupdated),
        ])
        return '[CR]'.join([app.shortdesc, '', facts])

    def app_dialog(self, app_id):
        if self.unsupported():
            return

        app = self.store.app(app_id)
        if not app:
            log('App %s not found' % app_id)
            return

        action_label = self.lang(32004) if app.installed else self.lang(32003)  # Uninstall/Install

        while True:
            choice = self.dialog.yesnocustom(app.name, self.details(app),
                                             customlabel=self.lang(32010),  # Information
                                             nolabel=self.lang(32016),  # Cancel
                                             yeslabel=action_label,
                                             defaultbutton=xbmcgui.DLG_YESNO_NO_BTN)
            if choice == CUSTOM:
                self.dialog.textviewer(app.name, app.longdesc or app.shortdesc)
                continue
            break

        if choice != YES:
            return

        if app.installed:
            action = 'removal_%s' % app.id
            notification = self.lang(32027) % app.name  # uninstalled
        else:
            action = 'install_%s' % app.id
            notification = self.lang(32026) % app.name  # installed

        log('Sending %s to the update service' % action)
        try:
            send_to_update_service(action, self.lang(32025), notification)
        except Exception as error:
            log('Update service did not answer: %s' % error)
            _ = self.dialog.ok(self.lang(32025), self.lang(32029))


def run(handle, params):
    AppStorePlugin(handle, params).run()
