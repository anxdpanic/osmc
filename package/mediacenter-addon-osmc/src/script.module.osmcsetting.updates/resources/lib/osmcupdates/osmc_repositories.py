# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 OSMC (KodeKarnage)

    This file is part of script.module.osmcsetting.updates

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import os
import subprocess
import sys
import traceback

import xbmcaddon
import xbmcgui
from aptsources.sourceslist import SourceEntry
from aptsources.sourceslist import SourcesList
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger

# --|start| will require updating--
APT_SOURCE = 'deb http://download.osmc.tv/dev/gmc-19/public gmc-19 main'
GPG_CERTIFICATE = 'http://download.osmc.tv/dev/gmc-19/public/pubkey.asc'
# --|end| will require updating--

ADDON_ID = 'script.module.osmcsetting.updates'
DIALOG = xbmcgui.Dialog()
PY2 = sys.version_info.major == 2

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


class OSMCRepositories:

    def __init__(self, addon=None):
        self._addon = addon
        self._lang = None
        self._source = SourceEntry(APT_SOURCE)
        self._sources_list = None

    def switch(self, branch='nightly'):
        if branch not in ('nightly', 'stable'):
            return

        if branch == 'nightly':
            self.add_repository()
            self.import_gpg_certificate()

        elif branch == 'stable':
            self.remove_repository()

    def nightly_repository_exists(self):
        source_type, source_uri, source_dist, source_comp = APT_SOURCE.split(' ')
        source_comps = [source_comp][:]

        sources = self.sources_list._SourcesList__find(
            lambda src: True, disabled=False, invalid=False,
            type=source_type, uri=source_uri, dist=source_dist
        )

        for source in sources:
            for comp in source_comps:
                if comp in source.comps:
                    del source_comps[source_comps.index(comp)]
                    if len(source_comps) == 0:
                        return True

        return False

    def add_repository(self):
        source = APT_SOURCE.split(' ')
        source[-1] = [source[-1]]
        self.sources_list.backup('osmc_repo')
        try:
            self.sources_list.add(*source)
            self.sources_list.save()
        except:
            self.sources_list.restore_backup('osmc_repo')

    def remove_repository(self):
        self.sources_list.backup('osmc_repo')
        try:
            self.sources_list.remove(self._source)
            self.sources_list.save()
        except ValueError:
            pass
        except:
            self.sources_list.restore_backup('osmc_repo')

    @staticmethod
    def import_gpg_certificate():
        try:
            _ = subprocess.check_call('wget -qO - ' + GPG_CERTIFICATE + ' | sudo apt-key add -',
                                      shell=True)
        except:
            traceback.print_exc()

    @property
    def addon(self):
        if not self._addon:
            self._addon = xbmcaddon.Addon(ADDON_ID)
        return self._addon

    def lang(self, value):
        if not self._lang:
            retriever = LangRetriever(self.addon)
            self._lang = retriever.lang
        return self._lang(value)

    @property
    def sources_list(self):
        if not self._sources_list:
            self._sources_list = SourcesList()
        return self._sources_list
