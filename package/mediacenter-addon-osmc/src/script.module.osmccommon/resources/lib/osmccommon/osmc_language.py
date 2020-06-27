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

    def __init__(self, addon):

        self.__addon__ = addon
        self._py2 = sys.version_info.major == 2

    def lang(self, string_id):

        if self.__addon__ is not None:

            if self._py2:
                return self.__addon__.getLocalizedString(string_id).encode('utf-8', 'ignore')

            return self.__addon__.getLocalizedString(string_id)

        return ''
