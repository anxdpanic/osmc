import socket
import sys

import xbmc
import xbmcgui
import xbmcaddon

__addon__ = xbmcaddon.Addon()
__setting__ = __addon__.getSetting
DIALOG = xbmcgui.Dialog()

PY2 = sys.version_info.major == 2
PY3 = sys.version_info.major == 3


def log(message):
    try:
        message = str(message)
    except UnicodeEncodeError:
        message = message.encode('utf-8', 'ignore')

    xbmc.log(message, level=xbmc.LOGDEBUG)


def lang(string_id):
    if PY2:
        return __addon__.getLocalizedString(string_id).encode('utf-8', 'ignore')
    return __addon__.getLocalizedString(string_id)


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
