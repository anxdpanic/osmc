# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.services

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import os

from osmccommon import osmc_setting
from osmccommon.osmc_logging import StandardLogger

from .. import services

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
        services.run(addon=self.me)
