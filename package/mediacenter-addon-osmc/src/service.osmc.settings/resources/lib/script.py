# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of service.osmc.settings

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import sys

if __name__ == '__main__':
    if sys.argv and sys.argv[0].startswith('plugin://'):
        from osmcsettings import plugin_entry

        plugin_entry.run(sys.argv)

    else:
        from osmcsettings import script_entry

        script_entry.run()
