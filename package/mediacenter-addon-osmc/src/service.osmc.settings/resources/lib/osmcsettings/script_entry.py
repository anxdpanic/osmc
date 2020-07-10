# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of service.osmc.settings

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import os
import socket
import sys

import xbmcaddon
import xbmcgui
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger

ADDON_ID = 'service.osmc.settings'
ADDRESS = '/var/tmp/osmc.settings.sockfile'
PY3 = sys.version_info.major == 3


def run():
    log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log

    log('My OSMC opening')
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(ADDRESS)
        open_cmd = 'open'
        if PY3:
            open_cmd = open_cmd.encode('utf-8')
        sock.sendall(open_cmd)
        sock.close()

    except:
        log('My OSMC failed to open')
        lang = LangRetriever(xbmcaddon.Addon(ADDON_ID)).lang
        _ = xbmcgui.Dialog().ok(lang(32047), '[CR]'.join([lang(32007), lang(32005)]))

    log('My OSMC closing')
