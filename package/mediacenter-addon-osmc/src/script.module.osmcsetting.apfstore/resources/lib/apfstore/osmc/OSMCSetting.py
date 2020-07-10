# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.apfstore

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import os

from osmccommon import osmc_setting
from osmccommon.osmc_logging import StandardLogger
from osmccommon.osmc_logging import clog

from ..apf_store import APF_STORE

addon_id = "script.module.osmcsetting.apfstore"
log = StandardLogger(addon_id, os.path.basename(__file__)).log


class OSMCSettingClass(osmc_setting.OSMCSettingClass):
    def __init__(self):
        super(OSMCSettingClass, self).__init__()

        self.addon_id = addon_id

        self.path = os.path.dirname(os.path.abspath(__file__))

        self.short_name = 'App Store'

        self.description = """This module is where you can grab awesome APFs like ... """

    @clog(log, nowait=True)
    def run(self):
        _ = APF_STORE()
