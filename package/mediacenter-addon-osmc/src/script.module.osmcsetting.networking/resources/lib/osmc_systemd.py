import subprocess
import time
import os

def is_service_running(service_name):
    enabled = is_service_enabled(service_name)
    active = is_service_active(service_name)
    return enabled and active


def toggle_service(service_name, enable):
    if enable:
        update_service(service_name, 'enable')
        update_service(service_name, 'start')
    else:
        update_service(service_name, 'disable')
        update_service(service_name, 'stop')


def is_service_enabled(service_name):
    fnull = open(os.devnull, 'w')
    process = subprocess.call(['/bin/systemctl', 'is-enabled', service_name], stderr=fnull, stdout=fnull)
    fnull.close()
    if process == 0:
        return True
    return False


def is_service_active(service_name):
    fnull = open(os.devnull, 'w')
    process = subprocess.call(['/bin/systemctl', 'is-active', service_name], stderr=fnull, stdout=fnull)
    fnull.close()
    if process == 0:
        return True
    return False


def update_service(service_name, service_status):
    fnull = open(os.devnull, 'w')
    subprocess.call(['sudo', '/bin/systemctl', service_status, service_name], stderr=fnull, stdout=fnull)
    fnull.close()
    time.sleep(1)

def is_service_running(service_name):
    fnull = open(os.devnull, 'w')
    process = subprocess.call(['/bin/systemctl', 'status', service_name], stderr=fnull, stdout=fnull)
    fnull.close()
    if process == 0:
        return True
    return False
