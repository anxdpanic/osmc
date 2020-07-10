# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.remotes

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import os

from osmccommon import osmc_setting
from osmccommon.osmc_logging import StandardLogger
from osmccommon.osmc_logging import clog

from .. import remote_gui

addon_id = "script.module.osmcsetting.remotes"
log = StandardLogger(addon_id, os.path.basename(__file__)).log


class OSMCSettingClass(osmc_setting.OSMCSettingClass):

    def __init__(self):
        super(OSMCSettingClass, self).__init__()

        self.addon_id = addon_id

        self.path = os.path.dirname(os.path.abspath(__file__))

        self.short_name = 'Remotes'

        self.description = """This module allows the user to select the appropriate lirc.conf file for their remote."""

    @clog(log, nowait=True)
    def run(self):
        self.GUI = remote_gui.remote_gui_launcher()
        self.GUI.open_gui()
