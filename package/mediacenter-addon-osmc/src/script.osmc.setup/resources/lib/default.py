# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.osmc.setup

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import sys

if __name__ == '__main__':
    from osmcsetup import setup_entry

    setup_entry.run(sys.argv)
