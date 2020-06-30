#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.logging

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

from osmccommon import grablogs

try:
    import xbmc
    import xbmcaddon
except ImportError:
    xbmc = None
    xbmcaddon = None

if __name__ == "__main__":

    addonid = "script.module.osmcsetting.logging"

    if not xbmc:
        copy, termprint = grablogs.parse_arguments()
    else:
        copy, termprint = grablogs.retrieve_settings(xbmcaddon.Addon(addonid))

    if copy is not None:
        m = grablogs.Main(copy, termprint)

        m.launch_process()
