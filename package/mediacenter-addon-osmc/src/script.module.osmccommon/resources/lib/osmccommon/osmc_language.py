# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 OSMC (KodeKarnage)

    This file is part of script.module.osmccommon

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import sys


class LangRetriever(object):
    """ Used to retrieve localised strings from the addons po files.

        Requires the parent addon object. This takes the form in that parent script of:
            __addon__ = xbmcaddon.Addon()

        Best usage:
            from osmc_language import LangRetriever
            LangRet = LangRetriever(__addon__)
            lang    = LangRet.lang

        """

    def __init__(self, addon=None):

        self.__addon__ = addon
        self._py2 = sys.version_info.major == 2

    def lang(self, string_id):
        if self.__addon__ is None:
            return str(string_id)

        if self.__addon__ is not None:

            if self._py2:
                return self.__addon__.getLocalizedString(string_id).encode('utf-8', 'ignore')

            return self.__addon__.getLocalizedString(string_id)

        return ''
