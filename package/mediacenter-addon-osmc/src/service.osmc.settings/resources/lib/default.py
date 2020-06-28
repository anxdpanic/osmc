import os
import socket
import sys

import xbmcgui
import xbmcaddon

from osmccommon.osmc_logging import StandardLogger
from osmccommon.osmc_language import LangRetriever

addonid = 'service.osmc.settings'
__addon__ = xbmcaddon.Addon(addonid)
__setting__ = __addon__.getSetting

DIALOG = xbmcgui.Dialog()

PY3 = sys.version_info.major == 3

log = StandardLogger(addonid, os.path.basename(__file__)).log
lang = LangRetriever(__addon__).lang

log('default started')

try:

    address = '/var/tmp/osmc.settings.sockfile'
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(address)
    open_cmd = 'open'
    if PY3:
        open_cmd = open_cmd.encode('utf-8')
    sock.sendall(open_cmd)
    sock.close()

except:

    log('default failed to open')

    ok = DIALOG.ok(lang(32007), '[CR]'.join([lang(32005), lang(32006)]))

log('default closing')
