# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.osmc.setup

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    RunScript(script.osmc.setup): the first-run setup. The settings service starts it on
    first run, after making skin.osmc the skin.

    RunScript(script.osmc.setup,test): My OSMC's "Test walk through". The same steps, but
    Back leaves from the first one and Finish applies nothing.
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

    testing = 'test' in (argv or [])[1:]

    home.setProperty(RUNNING, 'true')
    state = None
    try:
        state = show(testing)
    except Exception:
        log(traceback.format_exc(), xbmc.LOGERROR)
    finally:
        home.clearProperty(RUNNING)

    if testing:
        return

    if not (state and state.finished):
        # setup failed or Kodi is closing: it runs again at the next start, and until
        # then Kodi must not go on believing that setup is showing
        system.release_walkthrough_status()
        return

    if state.finished:
        xbmc.executebuiltin('ActivateWindow(Home)')
        if state.check_updates and state.online:
            system.request_update_check()


def show(testing=False):
    from .window import SetupWindow

    addon = xbmcaddon.Addon(ADDON_ID)
    monitor = xbmc.Monitor()

    state = Answers(vero=system.is_vero(), online=is_online(), hostname=system.hostname())
    try:
        state.ssh = system.is_ssh_enabled()
    except Exception:
        log(traceback.format_exc())
    state.testing = testing

    while not monitor.abortRequested():
        # strings are read again each time, as a new language changes them
        lang = LangRetriever(xbmcaddon.Addon(ADDON_ID)).lang
        window = SetupWindow(XML, addon.getAddonInfo('path'), 'Default', '1080i',
                             state=state, lang=lang)
        window.doModal()
        del window

        if state.finished or state.failed:
            break

        if state.pending_language:
            log('Changing the language to %s' % state.pending_language)
            system.set_language(state.pending_language)
            state.pending_language = None
            if monitor.waitForAbort(LANGUAGE_RELOAD_WAIT):
                break
            continue

        if state.testing:
            break

        # setup cannot be left before Finish: anything else that closed it reopens it
        log('Setup closed before Finish; reopening')
        if monitor.waitForAbort(1):
            break

    return state
