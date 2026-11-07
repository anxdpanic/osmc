# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.osmc.setup

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    RunScript(script.osmc.setup): the first-run setup. The settings service starts it on
    first run and from My OSMC's "Test walk through", after making skin.osmc the skin.
"""

import os
import traceback

import xbmc
import xbmcaddon
import xbmcgui
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger

from . import system
from .answers import Answers

ADDON_ID = 'script.osmc.setup'
XML = 'script-osmc-setup.xml'

# set on the Home window while setup shows, so it never opens twice
RUNNING = 'OSMCSetup.Running'

# Kodi reloads its interface after a new language; setup waits this long before reopening
LANGUAGE_RELOAD_WAIT = 3

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


def is_online():
    try:
        from osmcnetworking import osmc_network
        return osmc_network.has_network_connection(True)
    except Exception:
        log(traceback.format_exc())
        return False


def run(argv=None):
    home = xbmcgui.Window(10000)
    if home.getProperty(RUNNING):
        log('Setup is already showing')
        return

    home.setProperty(RUNNING, 'true')
    try:
        state = show()
    finally:
        home.clearProperty(RUNNING)

    if state and state.finished:
        xbmc.executebuiltin('ActivateWindow(Home)')
        if state.check_updates and state.online:
            system.request_update_check()


def show():
    from .window import SetupWindow

    addon = xbmcaddon.Addon(ADDON_ID)
    monitor = xbmc.Monitor()

    state = Answers(vero=system.is_vero(), online=is_online(), hostname=system.hostname())
    try:
        state.ssh = system.is_ssh_enabled()
    except Exception:
        log(traceback.format_exc())

    while not monitor.abortRequested():
        # strings are read again each time, as a new language changes them
        lang = LangRetriever(xbmcaddon.Addon(ADDON_ID)).lang
        window = SetupWindow(XML, addon.getAddonInfo('path'), 'Default', '1080i',
                             state=state, lang=lang)
        window.doModal()
        del window

        if state.finished:
            break

        if state.pending_language:
            log('Changing the language to %s' % state.pending_language)
            system.set_language(state.pending_language)
            state.pending_language = None
            if monitor.waitForAbort(LANGUAGE_RELOAD_WAIT):
                break
            continue

        # setup cannot be left before Finish: anything else that closed it reopens it
        log('Setup closed before Finish; reopening')
        if monitor.waitForAbort(1):
            break

    return state
