import sys
import socket

PY3 = sys.version_info.major == 3

if len(sys.argv) > 1:

    message = sys.argv[1]

    print('OSMC settings sending response, %s' % message)

    address = '/var/tmp/osmc.settings.sockfile'

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(address)
    if PY3:
        message = message.encode('utf-8', 'ignore')
    sock.sendall(message)
    sock.close()

    print('OSMC settings sent response, %s' % message)
