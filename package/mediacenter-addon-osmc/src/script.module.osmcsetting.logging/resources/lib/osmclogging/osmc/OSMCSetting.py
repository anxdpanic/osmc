# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.logging

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import os

import xbmc
import xbmcaddon
from osmccommon import osmc_setting
from osmccommon.osmc_logging import StandardLogger
from osmccommon.osmc_logging import clog

addonid = "script.module.osmcsetting.logging"
log = StandardLogger(addonid, os.path.basename(__file__)).log


class OSMCSettingClass(osmc_setting.OSMCSettingClass):

    def __init__(self):
        super(OSMCSettingClass, self).__init__()

        self.addonid = addonid
        self.me = xbmcaddon.Addon(addonid)

        self.path = os.path.join(xbmc.translatePath(self.me.getAddonInfo('path')), 'resources', 'lib', 'osmclogging', 'osmc')

        self.shortname = 'Log Uploader'

        self.description = """This module helps with debugging and troubleshooting by retrieving logs, various xml, and config information from your system and uploading them in a single file.[CR]
        Once uploading is complete, you are provided with a URL which you can share on the OSMC forums.[CR]
        The information stored in the URL will help others diagnose your issue and decrease the amount of time it takes to find a resolution. """

    @clog(log, nowait=True)
    def run(self):
        super(OSMCSettingClass, self).run()
