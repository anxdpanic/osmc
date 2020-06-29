# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.apfstore

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import hashlib
import os
from io import open

import xbmc
import xbmcaddon
import xbmcgui
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger
from osmccommon.osmc_logging import clog

addonid = "script.module.osmcsetting.apfstore"
__addon__ = xbmcaddon.Addon(addonid)
__path__ = xbmc.translatePath(xbmcaddon.Addon(addonid).getAddonInfo('path'))

ADDONART = os.path.join(__path__, 'resources', 'skins', 'Default', 'media')
USERART = os.path.join(xbmc.translatePath('special://userdata/'), 'addon_data', addonid)

log = StandardLogger(addonid, os.path.basename(__file__)).log
lang = LangRetriever(__addon__).lang

"""
=========================
APF JSON STRUCTURE
=========================

{
   "application": [
       {
           "id": "ssh-app-osmc",
           "name": "SSH Server",
           "shortdesc": "This allows you to connect to your OSMC device via SSH",
           "longdesc": "This installs an OpenSSH server on your OSMC device allowing you to log in to your device remotely as well as transfer files via SCP.",
           "maintained-by": "OSMC",
           "version": "1.0.0",
           "lastupdated": "2015-01-23",
       }
   ]
}
"""


class APF_obj(xbmcgui.ListItem):

    def __init__(self):

        xbmcgui.ListItem.__init__(self)

    def populate(self, data):

        self.id = data.get('id', 'none')
        self.name = data.get('name', 'none')
        self.shortdesc = data.get('shortdesc', '')
        self.longdesc = data.get('longdesc', '')
        self.maintainedby = data.get('maintained-by', '')
        self.version = data.get('version', '')
        self.lastupdated = data.get('lastupdated', '')
        self.iconurl = data.get('iconurl', '/none')
        self.iconhash = data.get('iconhash', 0)
        self.retrieve_icon = False
        self.current_icon = self.check_icon(self.iconurl)

        self.installed = False

        self.setLabel(self.name)
        self.setProperty('Addon.Description', self.longdesc)
        self.setProperty('Addon.Creator', self.maintainedby)
        self.setProperty('Addon.Name', self.name)
        self.setProperty('Addon.Version', self.version)
        self.setArt({
            'icon': self.current_icon
        })

        return self

    def set_installed(self, status):

        if status == True:
            self.installed = True
            self.setLabel2(lang(32005))

    def refresh_icon(self):

        self.current_icon = self.check_icon(self.iconurl)
        self.setArt({
            'icon': self.current_icon
        })

    @clog(logger=log)
    def check_icon(self, iconurl):
        """ Checks the addon data folder for the icon,
                if not found, check for an icon stored in the addon/media folder,
                    if not found there, mark the new icon for download by Main in a different thread,
                    use default substitute in the meantime
                if found, check the hash matches, if not mark new icon for download by Main in another thread,
                    use existing in meantime
        """

        if self.iconhash == 'NA':
            return os.path.join(ADDONART, 'osmc_osmclogo.png')

        icon_name = iconurl.split('/')[-1]

        if os.path.isfile(os.path.join(USERART, icon_name)):
            # check userdata folder

            current_icon = os.path.join(USERART, icon_name)

        elif os.path.isfile(os.path.join(ADDONART, icon_name)):
            # check addon art folder

            current_icon = os.path.join(ADDONART, icon_name)

        else:

            current_icon = os.path.join(ADDONART, 'osmc_osmclogo.png')

        log('current icon = %s' % current_icon)

        # get the hash
        with open(current_icon, 'rb') as open_file:
            icon_image = open_file.read()

        icon_hash = hashlib.md5(icon_image).hexdigest()

        if icon_hash != self.iconhash:
            self.retrieve_icon = True

        return current_icon
