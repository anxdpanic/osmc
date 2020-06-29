#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of service.osmc.settings

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import os

from osmcsettings import osmc_main as m

from osmccommon.osmc_logging import StandardLogger

log = StandardLogger('service.osmc.settings', os.path.basename(__file__)).log

if __name__ == "__main__":
    m.set_version()

    Main_Service = m.Main()

    log('Exiting OSMC Settings')
