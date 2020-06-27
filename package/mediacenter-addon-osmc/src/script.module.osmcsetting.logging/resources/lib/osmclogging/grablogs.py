#!/usr/bin/env python2

from osmccommon import grablogs

try:
    import xbmc
except ImportError:
    xbmc = None

if __name__ == "__main__":

    if not xbmc:
        copy, termprint = grablogs.parse_arguments()
    else:
        copy, termprint = grablogs.retrieve_settings()

    if copy is not None:
        m = grablogs.Main(copy, termprint)

        m.launch_process()
