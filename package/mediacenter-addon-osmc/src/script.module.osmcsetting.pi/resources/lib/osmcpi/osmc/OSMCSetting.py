# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.pi

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import os
import subprocess
import sys
import traceback

import xbmcaddon
import xbmcgui
from osmccommon import osmc_setting
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger

from .. import OSMC_REparser as parser

addon_id = "script.module.osmcsetting.pi"
DIALOG = xbmcgui.Dialog()

PY3 = sys.version_info.major == 3

log = StandardLogger(addon_id, os.path.basename(__file__)).log


class OSMCSettingClass(osmc_setting.OSMCSettingClass):

    def __init__(self):
        super(OSMCSettingClass, self).__init__()

        self.addon_id = addon_id

        self.path = os.path.dirname(os.path.abspath(__file__))

        self.short_name = 'Pi Config'

        self.description = """This is the text that is shown on the OSG. [CR][CR]It should describe:[CR]   - what the settings module is for,[CR]   - the settings it controls,[CR]   - and anything else you want, I suppose."""

        self.description = """The Raspberry Pi doesn't have a conventional BIOS. System configuration parameters are stored in a "config.txt" file. For more detail, visit http://elinux.org/RPiconfig[CR]
This settings module allows you to edit your config.txt from within OSMC using a graphical interface.

The module includes:
- display rotation
- hdmi_safe & hdmi_boost
- hdmi_group & hdmi_mode
- function to save edid to file
- sdtv_mode & sdtv_aspect
- GPU memory split
- MPG2 & WVC1 licences (including status)
- your Pi's serial number

Finally, there is a Config Editor that will allow you to quickly add, edit, or delete lines in your config.txt.

Overclock settings are set using the Pi Overclock module."""

        retriever = LangRetriever(self.me)
        self.lang = retriever.lang

        # the location of the config file FOR TESTING ONLY
        try:
            self.config_location = '/boot/config.txt'

            self.populate_misc_info()

        except:

            # if anything fails above, assume we are testing and look for the config
            # in the testing location
            self.config_location = '/home/plaskev/Documents/config.txt'

        try:
            self.clean_user_config()
        except Exception:

            log('Error cleaning users config')
            log(traceback.format_exc())

    def run(self):
        # read the config.txt file everytime the settings are opened. This is unavoidable because it is possible for
        # the user to have made manual changes to the config.txt while OSG is active.
        config = parser.read_config_file(self.config_location)

        extracted_settings = parser.config_to_kodi(parser.MASTER_SETTINGS, config)

        # load the settings into kodi
        log('Settings extracted from the config.txt')
        for k, v in extracted_settings.items():
            log("%s : %s" % (k, v))
            self.me.setSetting(k, str(v))

        # open the settings GUI and let the user monkey about with the controls
        self.me.openSettings()

        # retrieve the new settings from kodi
        new_settings = self.settings_retriever_xml()

        log('New settings applied to the config.txt')
        for k, v in new_settings.items():
            log("%s : %s" % (k, v))

        # read the config into a list of lines again
        config = parser.read_config_file(self.config_location)

        # construct the new set of config lines using the protocols and the new settings
        new_settings = parser.kodi_to_config(parser.MASTER_SETTINGS, config, new_settings)

        # write the new lines to the temporary config file
        parser.write_config_file('/var/tmp/config.txt', new_settings)

        # copy over the temp config.txt to /boot/ as superuser
        subprocess.call(["sudo", "mv", '/var/tmp/config.txt', self.config_location])

        DIALOG.notification(self.lang(32095), self.lang(32096))

    def settings_retriever_xml(self):
        latest_settings = {}

        addon = xbmcaddon.Addon(self.addon_id)

        for key in parser.MASTER_SETTINGS.keys():
            latest_settings[key] = addon.getSetting(key)

        return latest_settings

    def populate_misc_info(self):
        # grab the Pi serial number and check to see whether the codec licences are enabled
        mpg = subprocess.check_output(["/opt/vc/bin/vcgencmd", "codec_enabled", "MPG2"])
        wvc = subprocess.check_output(["/opt/vc/bin/vcgencmd", "codec_enabled", "WVC1"])
        serial_raw = subprocess.check_output(["cat", "/proc/cpuinfo"])

        if PY3:
            if isinstance(mpg, (bytes, bytearray)):
                mpg = mpg.decode('utf-8', 'ignore')
            if isinstance(wvc, (bytes, bytearray)):
                wvc = wvc.decode('utf-8', 'ignore')
            if isinstance(serial_raw, (bytes, bytearray)):
                serial_raw = serial_raw.decode('utf-8', 'ignore')

        # grab just the serial number
        serial = serial_raw[serial_raw.index('Serial') + len('Serial'):].replace('\n', '').replace(':', '').replace(' ', '').replace('\t', '')

        # load the values into the settings gui
        self.me.setSetting('codec_check', mpg.replace('\n', '') + ', ' + wvc.replace('\n', ''))
        self.me.setSetting('serial', serial)

    def clean_user_config(self):
        """ Comment out problematic lines in the users config.txt """

        patterns = [

            r".*=.*\[remove\].*",
            r".*=remove",
        ]

        config = parser.read_config_file(self.config_location)

        new_config = parser.clean_config(config, patterns)

        # write the new lines to the temporary config file
        parser.write_config_file('/var/tmp/config.txt', new_config)

        # copy over the temp config.txt to /boot/ as superuser
        subprocess.call(["sudo", "mv", '/var/tmp/config.txt', self.config_location])
