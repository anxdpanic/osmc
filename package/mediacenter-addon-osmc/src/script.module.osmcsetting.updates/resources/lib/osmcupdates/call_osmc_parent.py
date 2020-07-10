# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.updates

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import socket
import sys

PY3 = sys.version_info.major == 3


def argv():
    return sys.argv


if len(argv()) > 1:
    message = argv()[1]

    print('OSMC settings sending response, %s' % message)

    address = '/var/tmp/osmc.settings.sockfile'

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(address)
    if PY3 and not isinstance(message, (bytes, bytearray)):
        message = message.encode('utf-8')
    sock.sendall(message)
    sock.close()

    print('OSMC settings sent response, %s' % message)
