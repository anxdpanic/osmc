# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of service.osmc.settings

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    Finds the installed My OSMC modules, publishes them to the Home window
    for the My OSMC plugin folder and the skin's widgets, and launches them.
"""

import os
import sys
import threading
import traceback
from io import open

import xbmcaddon
import xbmcgui
from osmccommon.osmc_language import LangRetriever
from osmccommon.osmc_logging import StandardLogger
from osmccommon.osmc_logging import clog

ADDON_ID = 'service.osmc.settings'

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log

# the order of the modules in My OSMC
KNOWN_MODULES_ORDER = {
    'osmcpi': 0,
    'osmcupdates': 1,
    'osmcnetworking': 2,
    'osmcremotes': 3,
    'apfstore': 4,
    'osmcservices': 5,
    'osmclogging': 6,
}

PROPERTY_PREFIX = 'MyOSMC.Module'


class ModuleRegistry(object):

    def __init__(self, addon=None, window=None):
        self._addon = addon
        self._lang = None
        self.window = window or xbmcgui.Window(10000)
        self.script_path = self.addon.getAddonInfo('path')

        self._hardware_prefix = ''
        self.module_tally = 1000

        self.live_modules = []
        self.refresh()

    @property
    def addon(self):
        if not self._addon:
            self._addon = xbmcaddon.Addon(ADDON_ID)
        return self._addon

    def lang(self, value):
        if not self._lang:
            self._lang = LangRetriever(self.addon).lang
        return self._lang(value)

    @clog(log)
    def refresh(self):
        """ Finds the live modules and publishes them to the Home window """
        ordered_live_modules = self.retrieve_modules()
        ordered_live_modules.sort(key=lambda x: x[0])
        self.live_modules = [x[1] for x in ordered_live_modules]

        self.publish()

    def get(self, module_id):
        return next(iter(module for module in self.live_modules
                         if module.get('id') == module_id), None)

    def short_name(self, class_instance):
        short_name = getattr(class_instance, 'short_name', '')
        if isinstance(getattr(class_instance, 'short_name_i18n', None), int):
            short_name = self.lang(class_instance.short_name_i18n)
        return short_name

    def description(self, class_instance):
        description = getattr(class_instance, 'description', '')
        if isinstance(getattr(class_instance, 'description_i18n', None), int):
            description = self.lang(class_instance.description_i18n)
        return description

    def publish(self):
        """ Loads the information about each live module into the Home window,
            for the My OSMC plugin folder and the skin's My OSMC widget.
        """
        script_location = os.path.join(self.script_path, 'resources', 'lib', 'osmcsettings',
                                        'call_osmc_parent.py')

        self.window.setProperty('MyOSMC.Module.Script', script_location)

        # clear any modules published before that are now gone
        index = len(self.live_modules)
        while self.window.getProperty('%s.%s.id' % (PROPERTY_PREFIX, index)):
            for name in ('id', 'name', 'label', 'description', 'icon', 'fo_icon', 'fx_icon'):
                self.window.clearProperty('%s.%s.%s' % (PROPERTY_PREFIX, index, name))
            index += 1

        for index, module in enumerate(self.live_modules):
            class_instance = module['class_instance']
            prefix = '%s.%s' % (PROPERTY_PREFIX, index)

            # used by the skin's widget
            self.window.setProperty('%s.name' % prefix, class_instance.short_name)
            self.window.setProperty('%s.fo_icon' % prefix, class_instance.focused_widget)
            self.window.setProperty('%s.fx_icon' % prefix, class_instance.unfocused_widget)
            self.window.setProperty('%s.id' % prefix, module['id'])

            # used by the My OSMC plugin folder
            self.window.setProperty('%s.label' % prefix, self.short_name(class_instance))
            self.window.setProperty('%s.description' % prefix, self.description(class_instance))
            self.window.setProperty('%s.icon' % prefix, class_instance.focused_icon)

        self.window.setProperty('MyOSMC.Module.Count', str(len(self.live_modules)))

    def launch(self, module_id):
        """ Opens a module, then applies its settings once it closes """
        module = self.get(module_id)
        if not module:
            return False

        class_instance = module.get('class_instance')
        if class_instance and class_instance.is_alive():
            log('%s is already open' % module_id)
            class_instance.run()
            return True

        log('Opening %s' % module_id)
        class_instance = module['module_instance'].OSMCSettingClass()
        class_instance.daemon = True
        module['class_instance'] = class_instance

        def _run():
            class_instance.start()
            class_instance.join()
            try:
                class_instance.apply_settings()
            except Exception:
                log('apply_settings failed for %s' % module_id)
                log(traceback.format_exc())

        threading.Thread(target=_run, daemon=True).start()
        return True

    @clog(log)
    def retrieve_modules(self):
        """
            Imports each known module that is installed and returns a list of tuples:
            (order, {id, class_instance, module_instance})
        """
        self.module_tally = 1000

        return [x for x in [self.inspect_module(module_name)
                            for module_name in KNOWN_MODULES_ORDER.keys()] if x[1]]

    def inspect_module(self, module_name):
        log('Inspecting OSMC Setting module __ %s __' % module_name)
        try:
            if module_name == 'osmcpi' and not self.hardware_prefix.startswith('rbp'):
                return -1, None

            module_instance = __import__('%s.osmc.osmc_setting' % module_name, fromlist=[''])
            class_instance = module_instance.OSMCSettingClass()
            class_instance.daemon = True
        except:
            exc_type, exc_value, _ = sys.exc_info()
            log('OSMCSetting __ %s __ failed to import' % module_name)
            log(exc_type)
            log(exc_value)
            log(traceback.format_exc())
            return -1, None

        if not (class_instance.unfocused_icon and class_instance.focused_icon and
                class_instance.unfocused_widget and class_instance.focused_widget):
            return -1, None

        log('OSMC Setting module __ %s __ found and imported' % module_name)

        if module_name in KNOWN_MODULES_ORDER:
            order = KNOWN_MODULES_ORDER[module_name]
        else:
            order = self.module_tally
            self.module_tally += 1

        return order, {
            'id': module_name,
            'class_instance': class_instance,
            'module_instance': module_instance
        }

    @property
    def hardware_prefix(self):
        """ Returns the prefix for the hardware type. rbp, rbp2, etc """
        if self._hardware_prefix:
            return self._hardware_prefix

        self._hardware_prefix = ''

        with open('/proc/cmdline', 'r', encoding='utf-8') as f:
            line = f.readline()

        for setting in line.split(' '):
            if setting.startswith('osmcdev='):
                self._hardware_prefix = setting[len('osmcdev='):]
                break

        return self._hardware_prefix
