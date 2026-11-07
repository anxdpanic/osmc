# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.pi

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    The config-user.txt editor, built from Kodi's own dialogs:
    Dialog().select of the file (New Entry first); a line opens Dialog().yesnocustom
    (Edit, Delete, Cancel); Edit and New Entry use the keyboard. Each change is
    written at once, after one backup copy per session. Back returns to Pi Config
    on its Config Editor category.

    Run from the Config Editor action in the Pi Config settings:
        RunScript($CWD/resources/lib/osmcpi/config_editor.py)
"""

import os
import socket
import subprocess
import time
from io import open

import xbmc
import xbmcaddon
import xbmcgui
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger

ADDON_ID = 'script.module.osmcsetting.pi'

CONFIG = '/boot/config-user.txt'
TEMP_CONFIG = '/var/tmp/config-user.txt'
BACKUP_FOLDER = '/home/pi/'

# keys that may appear more than once
IGNORE_DUPLICATES = ['dtoverlay', 'device_tree', 'device_tree_param',
                     'device_tree_overlay', 'dtparam']

# returning to Pi Config: the settings service opens the module again, then the
# Config Editor category button gets focus (Kodi numbers category buttons from -200)
SETTINGS_SOCKET = '/var/tmp/osmc.settings.sockfile'
PI_MODULE_ID = 'osmcpi'
WINDOW_DIALOG_ADDON_SETTINGS = 10140
CONFIG_EDITOR_CATEGORY = -197

# Dialog().yesnocustom: nolabel, yeslabel and customlabel are drawn in that order
EDIT = 0
DELETE = 1

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


def read_lines(config=CONFIG):
    try:
        with open(config, 'r', encoding='utf-8') as open_file:
            lines = open_file.readlines()
    except (IOError, OSError):
        log('Unable to read %s' % config)
        return []

    return [line.rstrip('\r\n') for line in lines if line.strip()]


def key_of(line):
    if '=' not in line or line.lstrip().startswith('#'):
        return None
    return line.split('=', 1)[0].strip()


def duplicate_keys(lines):
    keys = [key for key in (key_of(line) for line in lines)
            if key and key not in IGNORE_DUPLICATES]
    return {key for key in keys if keys.count(key) > 1}


def is_duplicate(entry, lines):
    """ True if entry's key is already set by one of lines """
    key = key_of(entry)
    if not key or key in IGNORE_DUPLICATES:
        return False
    return any(key_of(line) == key for line in lines)


class ConfigEditor(object):

    def __init__(self, addon=None, config=CONFIG):
        self._addon = addon
        self._lang = None
        self.config = config
        self.dialog = xbmcgui.Dialog()
        self.backed_up = False

    @property
    def addon(self):
        if not self._addon:
            self._addon = xbmcaddon.Addon(ADDON_ID)
        return self._addon

    def lang(self, value):
        if not self._lang:
            self._lang = LangRetriever(self.addon).lang
        return self._lang(value)

    def warn_duplicate(self):
        _ = self.dialog.ok(self.lang(32051), '[CR]'.join([self.lang(32067), self.lang(32066)]))

    def backup(self):
        """ Today's backup copy, once per editing session """
        if self.backed_up:
            return
        suffix = '_' + str(int(time.time()))
        subprocess.call(['sudo', 'cp', self.config,
                         os.path.join(BACKUP_FOLDER, 'config-user%s.txt' % suffix)])
        self.backed_up = True

    def write(self, lines):
        self.backup()

        with open(TEMP_CONFIG, 'w', encoding='utf-8') as open_file:
            for line in lines:
                open_file.write(line.replace(' = ', '=') + '\n')

        subprocess.call(['sudo', 'mv', TEMP_CONFIG, self.config])
        log('%s written' % self.config)

    def run(self):
        lines = read_lines(self.config)

        if duplicate_keys(lines):
            _ = self.dialog.ok(self.lang(32051), '[CR]'.join([self.lang(32065), self.lang(32066)]))

        preselect = 0
        while not xbmc.Monitor().abortRequested():
            # the file is the record: Pi Config may have written it as its settings closed
            lines = read_lines(self.config)
            items = [self.lang(32052)] + lines
            index = self.dialog.select(self.lang(32051), items, preselect=preselect)

            if index < 0:
                break

            if index == 0:
                preselect = self.new_entry(lines)
            else:
                preselect = self.edit_or_delete(lines, index - 1)

        self.back_to_settings()

    def new_entry(self, lines):
        entry = self.dialog.input(self.lang(32064), type=xbmcgui.INPUT_ALPHANUM)
        if not entry:
            return 0

        if is_duplicate(entry, lines):
            self.warn_duplicate()

        lines.append(entry)
        self.write(lines)
        return len(lines)  # the new line, after New Entry

    def edit_or_delete(self, lines, line_index):
        line = lines[line_index]
        choice = self.dialog.yesnocustom(line, self.lang(32057),
                                         customlabel=xbmc.getLocalizedString(222),  # Cancel
                                         nolabel=self.lang(32058),  # Edit
                                         yeslabel=self.lang(32059),  # Delete
                                         defaultbutton=xbmcgui.DLG_YESNO_NO_BTN)

        if choice == DELETE:
            del lines[line_index]
            self.write(lines)
            return min(line_index + 1, len(lines))

        if choice == EDIT:
            entry = self.dialog.input(self.lang(32060), line, type=xbmcgui.INPUT_ALPHANUM)
            if entry and entry != line:
                others = lines[:line_index] + lines[line_index + 1:]
                if is_duplicate(entry, others):
                    self.warn_duplicate()
                lines[line_index] = entry
                self.write(lines)

        return line_index + 1

    @staticmethod
    def back_to_settings():
        """ Opens Pi Config again through the settings service, on Config Editor """
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as open_socket:
                open_socket.connect(SETTINGS_SOCKET)
                open_socket.sendall(PI_MODULE_ID.encode('utf-8'))
        except Exception:
            log('My OSMC service did not answer, not reopening Pi Config')
            return

        monitor = xbmc.Monitor()
        for _ in range(50):
            if xbmcgui.getCurrentWindowDialogId() == WINDOW_DIALOG_ADDON_SETTINGS:
                xbmc.executebuiltin('SetFocus(%d)' % CONFIG_EDITOR_CATEGORY)
                return
            if monitor.waitForAbort(0.1):
                return
        log('Pi Config did not reopen')


if __name__ == '__main__':
    log('OPEN')
    # give Pi Config time to write its own changes to config-user.txt as it closes
    xbmc.sleep(150)
    ConfigEditor().run()
    log('CLOSED')
