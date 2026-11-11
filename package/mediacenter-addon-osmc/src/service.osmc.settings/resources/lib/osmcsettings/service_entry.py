#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of service.osmc.settings

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import json
import os
import subprocess
import traceback
from copy import deepcopy
from io import open

import xbmc
import xbmcaddon
import xbmcgui
from osmccommon.osmc_comms import Communicator
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger

from . import osmc_modules
from . import osmc_ubiquifonts

try:
    import queue as Queue
except ImportError:
    import Queue

ADDON_ID = 'service.osmc.settings'
PLUGIN_URL = 'plugin://%s/' % ADDON_ID

# the first-run setup, and the skin it is drawn in
SETUP_ID = 'script.osmc.setup'
SKIN_ID = 'skin.osmc'
ADDON = xbmcaddon.Addon(ADDON_ID)

DIALOG = xbmcgui.Dialog()

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log
lang = LangRetriever(ADDON).lang


class Main(object):

    def __init__(self, window):
        log('main addon starting')

        self.window = window
        self.set_version()

        # queue for communication with the comm and Main
        self.parent_queue = Queue.Queue()

        # create socket, listen for comms
        self.listener = Communicator(self.parent_queue, socket_file='/var/tmp/osmc.settings.sockfile')
        self.listener.start()

        # the installed My OSMC modules, published to the Home window for the plugin folder
        self.modules = osmc_modules.ModuleRegistry(addon=ADDON, window=self.window)

        # monitor created to check for xbmc abort requests
        self.monitor = xbmc.Monitor()

        # current skin directory, used to detect when the user has changed skins and the fonts need importing again
        self.skin_dir = xbmc.getSkinDir()

        self.fonts = osmc_ubiquifonts.UbiquiFonts(ADDON_ID, ADDON, self.window)

        # run the ubiquifonts script to import the needed fonts into the Font.xml
        _ = self.fonts.import_osmc_fonts()

        if not os.path.isfile('/walkthrough_completed'):
            # Tell Kodi that OSMC is running the walkthrough
            try:
                xbmc.setosmcwalkthroughstatus(1)
            except Exception:
                log(traceback.format_exc())
        else:
            try:
                # Tell Kodi that OSMC is done
                xbmc.setosmcwalkthroughstatus(2)
            except Exception:
                log(traceback.format_exc())

        # daemon
        self._daemon()

        log('_daemon exited')

    def _daemon(self):
        log('daemon started')

        if not os.path.isfile('/walkthrough_completed'):
            self._walk_through()  # start walk through

        while not self.monitor.abortRequested():
            if not self.parent_queue.empty():
                try:
                    response = self.parent_queue.get()
                    log('response : %s' % response)

                    abort_requested = self._handle_response(response=response)
                    if abort_requested:
                        break

                finally:
                    try:
                        self.parent_queue.task_done()
                    except:
                        pass

            # sleep for one second, exit if Kodi is shutting down
            if self.monitor.waitForAbort(1):
                break

            abort_requested = self._check_skin()
            if abort_requested:
                break

        log('_daemon exiting')
        self.exit()
        log('_daemon shutdown')

    def exit(self):
        # try to kill the gui and comms
        try:
            log('Stopping listener (in wait)')
            self.listener.stop()
            log('Deleting listener (in wait)')
            del self.listener
            log('Listener deleted.')

        except:
            log('Failed to stop/delete listener. (in wait)')

    @staticmethod
    def get_sources_list():
        query = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "Files.GetSources",
            "params": {}
        }
        xbmc_request = json.dumps(query)
        result_raw = xbmc.executeJSONRPC(xbmc_request)
        result = json.loads(result_raw)
        media_dict_raw = result.get('result', {}).get('sources', {})
        media_list_raw = [v.get('file', '') for k, v in media_dict_raw.items()]
        media_string = ''.join(media_list_raw)

        return media_string

    @staticmethod
    def open_my_osmc():
        log('Opening My OSMC')
        xbmc.executebuiltin('ActivateWindow(Programs,%s,return)' % PLUGIN_URL)

    @staticmethod
    def set_walkthrough_status(value):
        try:
            # Tell Kodi that OSMC is done
            xbmc.setosmcwalkthroughstatus(int(value))
        except Exception:
            log(traceback.format_exc())

    def set_version(self, overwrite=False):
        """ Loads the current OSMC version into the Home window for display in MyOSMC """

        # Check for "upgraded" Alpha 4 and earlier

        if not overwrite and self.window.getProperty('osmc_version'):
            return

        with open(os.devnull, 'w') as fnull:
            process = subprocess.call(['/usr/bin/dpkg-query', '-l', 'rbp-mediacenter-osmc'], stderr=fnull, stdout=fnull)

        if process == 0:

            version_string = 'Unsupported OSMC Alpha release'

        else:

            version = []

            with open('/etc/os-release', 'r', encoding='utf-8') as f:
                lines = f.readlines()

            tags = ['NAME=', 'VERSION=', 'VERSION_ID=']
            for line in lines:

                for tag in tags:

                    if line.startswith(tag):
                        version.append(line[len(tag):].replace('"', '').replace('\n', ''))

            version_string = ' '.join(version)

        log('Current Version: %s' % version_string)

        self.window.setProperty('osmc_version', version_string)

    def _check_skin(self):
        # Check the current skin directory, if it is different to the previous one, then
        # import the OSMC fonts into the new skin
        if self.skin_dir != xbmc.getSkinDir():

            log('Old Skin: %s' % self.skin_dir)

            self.skin_dir = xbmc.getSkinDir()

            log('New Skin: %s' % self.skin_dir)

            try:
                resp = self.fonts.import_osmc_fonts()

                log('Ubiquifonts result: %s' % resp)

                if resp == 'reload_please':

                    while not self.monitor.abortRequested():

                        if self.monitor.waitForAbort(1):
                            return True

                        xml = xbmc.getInfoLabel('Window.Property(xmlfile)')

                        if xml != 'DialogConfirm.xml':
                            log('Skin reload requested')

                            xbmc.executebuiltin('ReloadSkin()')

                            break

            except Exception:
                log(traceback.format_exc())

        return False

    def _walk_through(self):
        # Tell Kodi that OSMC is running the first-run setup; script.osmc.setup marks it done
        self.window.setProperty("walkthrough_is_running", 'any_value')
        self.set_walkthrough_status(1)
        self.run_setup()

    def run_setup(self):
        """ Makes skin.osmc the skin, without asking, then starts script.osmc.setup """
        for addon_id in (SKIN_ID, SETUP_ID):
            self.jsonrpc('Addons.SetAddonEnabled', {'addonid': addon_id, 'enabled': True})

        if xbmc.getSkinDir() != SKIN_ID:
            log('Setting the skin to %s' % SKIN_ID)
            try:
                xbmc.setskin(SKIN_ID)  # OSMC's Kodi: no "keep this skin?" question
            except Exception:
                self.jsonrpc('Settings.SetSettingValue', {'setting': 'lookandfeel.skin',
                                                          'value': SKIN_ID})
                # Kodi asks whether to keep the new skin; setup answers for the user
                if self.monitor.waitForAbort(2):
                    return
                if xbmc.getCondVisibility('Window.IsActive(yesnodialog)'):
                    xbmc.executebuiltin('SendClick(yesnodialog,11)')
            if self.monitor.waitForAbort(2):
                return
            self.skin_dir = xbmc.getSkinDir()

        log('Starting %s' % SETUP_ID)
        xbmc.executebuiltin('RunScript(%s)' % SETUP_ID)

    @staticmethod
    def jsonrpc(method, params):
        request = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        if 'error' in response:
            log('%s failed: %s' % (method, response['error']))
        return response.get('result')

    def _handle_response(self, response):
        if response in ('open', 'refresh_gui'):
            self.open_my_osmc()

        elif response == 'ping':
            # the My OSMC plugin checks the service is answering
            pass

        elif response == 'exit':
            return True  # signal abort

        elif response == 'walkthru':
            log('Running manually called setup')

            # a test: the skin stays, setup can be left, and Finish applies nothing
            self.jsonrpc('Addons.SetAddonEnabled', {'addonid': SETUP_ID, 'enabled': True})
            xbmc.executebuiltin('RunScript(%s,test)' % SETUP_ID)

        elif 'new_device:' in response:
            # a usb device is attached to the hardware

            # get the device id
            device_id = response[len('new_device:'):]

            # proceed only if the device_id is not null
            if device_id:

                # get ignore list
                ignore_list_raw = ADDON.getSetting('ignored_devices')
                ignore_list_initial = ignore_list_raw.split('|')
                ignore_list = deepcopy(ignore_list_initial)

                # get sources list
                media_string = self.get_sources_list()

                # post dialogs to ask the user if they want to add the source, or ignore the device
                if device_id not in ignore_list and device_id not in media_string:

                    result = DIALOG.yesno(lang(32002), '[CR]'.join([lang(32003), lang(32004)]))

                    if result:
                        xbmc.executebuiltin("ActivateWindow(mediasource)")

                    else:
                        result = DIALOG.yesno(lang(32002), lang(32005))

                        if result:
                            ignore_list.append(str(device_id))

                if ignore_list_initial != ignore_list:
                    ignore_string = '|'.join(ignore_list)
                    ADDON.setSetting('ignored_devices', ignore_string)

        else:
            # check whether the response is one of the live_modules, if it is then launch that module
            if not self.modules.launch(response):
                log('Unknown response: %s' % response)

        return False
