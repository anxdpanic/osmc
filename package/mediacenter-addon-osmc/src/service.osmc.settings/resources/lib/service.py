#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of service.osmc.settings

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

from osmcsettings import osmc_main

if __name__ == '__main__':
    osmc_main.set_version()
    osmc_main.Main()
