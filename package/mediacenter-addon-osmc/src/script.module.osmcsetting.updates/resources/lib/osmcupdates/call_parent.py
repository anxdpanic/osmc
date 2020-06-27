import sys
import socket
import json

PY3 = sys.version_info.major == 3

if len(sys.argv) > 1:
    msg = sys.argv[1]

    print('OSMC settings sending response, %s' % msg)

    address = '/var/tmp/osmc.settings.update.sockfile'

    message = ('settings_command', {
        'action': msg
    })

    message = json.dumps(message)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(address)
    if PY3 and not isinstance(message, (bytes, bytearray)):
        message = message.encode('utf-8')
    sock.sendall(message)
    sock.close()

    print('OSMC settings sent response, %s' % msg)
