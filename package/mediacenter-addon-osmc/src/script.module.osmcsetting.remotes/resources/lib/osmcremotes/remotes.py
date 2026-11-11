# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.remotes

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    Remotes: Dialog().select (useDetails) of the lircd.conf files, the active one
    preselected, then "Browse for a .conf file…" and "Disable RC6".
    A new remote is tested: DialogProgress while lircd_helper restarts (Cancel
    reverts), then a yes/no with Revert focused that reverts on its own after
    20 seconds; reaching Confirm proves the new remote works.
"""

import os
import subprocess
import time
from io import open

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger

ADDON_ID = 'script.module.osmcsetting.remotes'

ETC_LIRC = '/etc/lirc'
LIRCD_PATH = os.path.join(ETC_LIRC, 'lircd.conf')
EXCLUDED = ['lircd.conf']

RC6_FILE = '/etc/modprobe.d/blacklist-rc6.conf'
RC6_PAYLOAD = 'blacklist ir_rc6_decoder\ninstall ir_rc6_decoder /bin/true'

SERVICE_TIMEOUT = 10  # seconds for lircd_helper to come back
CONFIRM_TIMEOUT = 20  # seconds before an unconfirmed remote reverts

# lircd.conf as it was, when it is a file of its own and not a link to a conf
REVERT_COPY = '/var/tmp/lircd.conf.before-test'

BROWSE = 'browse'
RC6 = 'rc6'

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


def is_custom(conf):
    """ A conf file the user browsed to, outside /etc/lirc """
    return os.path.dirname(os.path.abspath(conf)) != ETC_LIRC


def conf_name(conf):
    """ The remote's name: '# name:' on the first line, otherwise the file name """
    try:
        with open(conf, 'r', encoding='utf-8', errors='ignore') as open_file:
            first_line = open_file.readline()
    except (IOError, OSError):
        first_line = ''

    if first_line.startswith('# name:'):
        return first_line[len('# name:'):].strip()

    return os.path.basename(conf).replace('.conf', '')


def conf_image(conf):
    image = os.path.splitext(conf)[0] + '.png'
    return image if os.path.isfile(image) else ''


def local_confs(directory=ETC_LIRC):
    """ The non-empty .conf files in /etc/lirc, sorted """
    confs = []
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return confs

    for name in names:
        conf = os.path.join(directory, name)
        if name in EXCLUDED or not name.endswith('.conf'):
            continue
        try:
            if not os.path.isfile(conf) or os.stat(conf).st_size == 0:
                continue
        except OSError:
            continue
        confs.append(conf)

    return confs


def fetch_conf(path):
    """ A browsed conf as a file on this device: one on the network is copied here first.
        Returns None if there is no such file. """
    if os.path.isfile(path):
        return path
    if not xbmcvfs.exists(path):
        return None

    folder = os.path.join(xbmcvfs.translatePath(xbmcaddon.Addon(ADDON_ID).getAddonInfo('profile')),
                          'remotes')
    xbmcvfs.mkdirs(folder)
    name = os.path.basename(path.rstrip('/').split('/')[-1]) or 'lircd.conf'
    local = os.path.join(folder, name)
    if not xbmcvfs.copy(path, local) or not os.path.isfile(local):
        log('Could not copy %s to %s' % (path, local))
        return None
    return local


def keep_copy():
    """ Copies a lircd.conf that is a file of its own, so a test can be reverted """
    if subprocess.call(['sudo', 'cp', '-p', LIRCD_PATH, REVERT_COPY]) == 0:
        return REVERT_COPY
    log('Could not copy %s' % LIRCD_PATH)
    return None


def restore_copy(copy):
    # the link goes first: cp would write through it, into the conf under test
    subprocess.call(['sudo', 'rm', '-f', LIRCD_PATH])
    subprocess.call(['sudo', 'cp', '-p', copy, LIRCD_PATH])


def active_conf():
    target = os.path.realpath(LIRCD_PATH)
    return target if os.path.isfile(target) else None


def rc6_disabled():
    return os.path.isfile(RC6_FILE)


def set_rc6_disabled(disable):
    if disable:
        log('Creating RC6 blacklist file')
        with open('/var/tmp/blacklist-rc6.conf', 'w', encoding='utf-8') as open_file:
            open_file.write(RC6_PAYLOAD)
        subprocess.call(['sudo', 'mv', '/var/tmp/blacklist-rc6.conf', RC6_FILE])
    else:
        log('Removing RC6 blacklist file')
        subprocess.call(['sudo', 'rm', '-f', RC6_FILE])


def link_conf(conf):
    subprocess.call(['sudo', 'ln', '-sf', conf, LIRCD_PATH])


def restart_service():
    return subprocess.Popen(['sudo', 'systemctl', 'restart', 'lircd_helper@*'])


class Remotes(object):

    def __init__(self, addon=None):
        self._addon = addon
        self._lang = None
        self.dialog = xbmcgui.Dialog()
        self.monitor = xbmc.Monitor()

    @property
    def addon(self):
        if not self._addon:
            self._addon = xbmcaddon.Addon(ADDON_ID)
        return self._addon

    def lang(self, value):
        if not self._lang:
            self._lang = LangRetriever(self.addon).lang
        return self._lang(value)

    def build_items(self, active):
        """ Returns (list items, matching values, index of the active remote) """
        confs = local_confs()
        if active and is_custom(active):
            confs = [active] + confs

        items = []
        values = []
        preselect = -1
        for conf in confs:
            list_item = xbmcgui.ListItem(label=conf_name(conf), label2=os.path.basename(conf),
                                         offscreen=True)
            image = conf_image(conf)
            if image:
                list_item.setArt({'icon': image, 'thumb': image})
            list_item.setProperty('fullpath', conf)
            if conf == active:
                preselect = len(items)
            items.append(list_item)
            values.append(conf)

        items.append(xbmcgui.ListItem(label=self.lang(32017), label2=self.lang(32018),
                                      offscreen=True))
        values.append(BROWSE)

        rc6_state = self.lang(32015) if rc6_disabled() else self.lang(32016)  # On / Off
        items.append(xbmcgui.ListItem(label=self.lang(32012), label2=rc6_state, offscreen=True))
        values.append(RC6)

        return items, values, preselect

    def run(self):
        focus = None
        while not self.monitor.abortRequested():
            active = active_conf()
            items, values, preselect = self.build_items(active)
            if focus in values:
                preselect = values.index(focus)

            index = self.dialog.select(self.lang(32019), items, preselect=preselect, useDetails=True)
            if index < 0:
                return

            choice = values[index]
            focus = choice

            if choice == RC6:
                set_rc6_disabled(not rc6_disabled())
                continue

            if choice == BROWSE:
                choice = self.dialog.browse(1, self.lang(32005), 'files', '.conf')
                choice = fetch_conf(choice) if choice else None
                if not choice:
                    continue

            if choice == active:
                log('%s is already the active remote' % choice)
                continue

            if self.test(choice):
                focus = choice
            else:
                focus = active

    def test(self, conf):
        """ Switches to conf and asks the user to confirm with the new remote.
            Reverts unless Confirm is reached. Returns True if the change is kept.
        """
        log('Testing remote conf: %s' % conf)
        original = os.readlink(LIRCD_PATH) if os.path.islink(LIRCD_PATH) else None
        saved = keep_copy() if original is None and os.path.isfile(LIRCD_PATH) else None

        link_conf(conf)
        result = self.wait_for_service()

        if result == 'running':
            if self.confirm():
                log('User confirmed the new remote works')
                return True
            log('New remote not confirmed, reverting')

        elif result == 'dead':
            log('Remote service failed to restart')

        else:
            log('User cancelled while the service restarted')

        if original:
            link_conf(original)
        elif saved:
            restore_copy(saved)
        restart_service().wait()

        if result == 'dead':
            _ = self.dialog.ok(self.lang(32006), self.lang(32013))

        return False

    def wait_for_service(self):
        """ DialogProgress while lircd_helper restarts; 'running', 'dead' or 'cancelled' """
        progress = xbmcgui.DialogProgress()
        progress.create(self.lang(32006), self.lang(32011))

        process = restart_service()
        deadline = time.time() + SERVICE_TIMEOUT
        try:
            while True:
                code = process.poll()
                if code is not None:
                    if code != 0:
                        log('systemctl restart lircd_helper returned %s' % code)
                    return 'running' if code == 0 else 'dead'

                if progress.iscanceled():
                    return 'cancelled'

                remaining = deadline - time.time()
                if remaining <= 0:
                    return 'dead'

                progress.update(int(100 * (SERVICE_TIMEOUT - remaining) / SERVICE_TIMEOUT))
                if self.monitor.waitForAbort(0.25):
                    return 'cancelled'
        finally:
            progress.close()

    def confirm(self):
        """ yes/no, Revert focused, closes itself after CONFIRM_TIMEOUT seconds """
        message = '[CR]'.join([self.lang(32007), self.lang(32014) % CONFIRM_TIMEOUT])

        # Writing a live countdown into the dialog's text control from another
        # thread crashed Kodi 21 on a Vero V, so the message states the timeout.
        return self.dialog.yesno(self.lang(32006), message,
                                 nolabel=self.lang(32009), yeslabel=self.lang(32010),
                                 autoclose=CONFIRM_TIMEOUT * 1000,
                                 defaultbutton=xbmcgui.DLG_YESNO_NO_BTN)


def run(addon=None):
    Remotes(addon).run()
