# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.remotes

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import os

import xbmc
import xbmcaddon
from osmccommon import osmc_setting
from osmccommon.osmc_logging import StandardLogger
from osmccommon.osmc_logging import clog

from .. import remote_gui

addonid = "script.module.osmcsetting.remotes"
log = StandardLogger(addonid, os.path.basename(__file__)).log


class OSMCSettingClass(osmc_setting.OSMCSettingClass):

    def __init__(self):
        super(OSMCSettingClass, self).__init__()

        self.addonid = addonid
        self.me = xbmcaddon.Addon(addonid)

        self.path = os.path.join(xbmc.translatePath(self.me.getAddonInfo('path')), 'resources', 'lib', 'osmcremotes', 'osmc')

        self.shortname = 'Remotes'

        self.description = """This module allows the user to select the appropriate lirc.conf file for their remote."""

    @clog(log, nowait=True)
    def run(self):
        self.GUI = remote_gui.remote_gui_launcher()
        self.GUI.open_gui()
