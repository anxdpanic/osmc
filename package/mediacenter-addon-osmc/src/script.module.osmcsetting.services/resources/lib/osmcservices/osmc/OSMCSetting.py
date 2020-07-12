# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.services

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import os

import xbmcgui
from osmccommon import osmc_setting
from osmccommon.osmc_logging import StandardLogger

from ..service_selection_gui import service_selection

addon_id = "script.module.osmcsetting.services"
log = StandardLogger(addon_id, os.path.basename(__file__)).log


class OSMCSettingClass(osmc_setting.OSMCSettingClass):

    def __init__(self):
        super(OSMCSettingClass, self).__init__()

        self.addon_id = addon_id

        self.short_name = 'Services'
        self.short_name_i18n = 32058

        self.description = 'Control OSMC services'
        self.description_i18n = 32059

        self.setting_data_method = {

            'none': {
                'setting_value': '',
            }

        }

        self.reboot_required = False

    def run(self):
        scriptPath = self.me.getAddonInfo('path')

        # 						( s_entry, service_name, running, enabled )

        service_list = {
            'test1b': ('test1', 'test1a', ' (running)', True),
            'test2b': ('test2', 'test2a', ' (enabled)', True),
            'test3b': ('test3', 'test3a', '', False)
        }

        xml = "ServiceBrowser_720OSMC.xml" if xbmcgui.Window(10000).getProperty("SkinHeight") == '720' else "ServiceBrowser_OSMC.xml"

        creation = service_selection(xml, scriptPath, 'Default', service_list=service_list, logger=log)
        creation.doModal()
        del creation
