# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.apfstore

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import os

import xbmc

from osmccommon import osmc_setting
from osmccommon.osmc_logging import StandardLogger
from osmccommon.osmc_logging import clog

addon_id = "script.module.osmcsetting.apfstore"
PLUGIN_URL = 'plugin://service.osmc.settings/?module=apfstore'
log = StandardLogger(addon_id, os.path.basename(__file__)).log


class OSMCSettingClass(osmc_setting.OSMCSettingClass):
    def __init__(self):
        super(OSMCSettingClass, self).__init__()

        self.addon_id = addon_id

        self.short_name = 'App Store'
        self.short_name_i18n = 32048

        self.description = 'This module is where you can grab awesome APFs like...'
        self.description_i18n = 32049

        # My OSMC lists the App Store as a folder, see apfstore/plugin.py
        self.plugin_folder = True

    @clog(log, nowait=True)
    def run(self):
        # opened from elsewhere, e.g. the skin's My OSMC widget: show the folder
        xbmc.executebuiltin('ActivateWindow(Programs,%s,return)' % PLUGIN_URL)
