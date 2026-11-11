# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2026 OSMC (KodeKarnage)

    This file is part of script.osmc.setup

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.

    The setup window: one dialog, the same layout on every step. The step's icon and help
    text sit on the left, its options (or a list, the wired settings, the summary or a legal
    text) on the right, centred on the list area, and Back and Done below.

    The skin draws it from script-osmc-setup.xml; these ids and window properties are the
    contract between the two:
        21, 22      Back, Done (in grouplist 9001)
        100         the options; ListItem.Label2 holds a value, ListItem.Property(kind) is
                    button, switch or readonly, ListItem.Property(on) a switch's state
        200         a list shown in place (languages, regions, Wi-Fi, countries, timezones)
        300, 301    a legal text and its scrollbar
        400         the summary's answers
        Window.Property(Setup.Mode)     options, picker, wired, text, summary or remote
        Window.Property(Setup.Step)     the step's id, as in answers.STEPS
        Window.Property(Setup.Title)    the step's name
        Window.Property(Setup.Icon)     the step's icon
        Window.Property(Setup.Help)     the help text under the icon
        Window.Property(Setup.Remote)   the Remote step's text, on the right
        Window.Property(Setup.Clock)    set once Timezone is done
        Window.Property(Setup.Changing) set while one step fades into the next
"""

import os
import threading
import traceback

import xbmc
import xbmcgui
from osmccommon.osmc_logging import StandardLogger

from . import answers as setup_answers
from . import legal_license
from . import legal_warranty
from . import system
from .network_step import NetworkStep

ADDON_ID = 'script.osmc.setup'

BACK = 21
DONE = 22
BUTTONS = 9001
OPTIONS = 100
PICKER = 200
TEXT = 300
SUMMARY = 400

ROW_HEIGHT = 58
PICKER_ROWS = 12
LIST_MIDDLE = 540  # the middle of the list area, y 192 to 888

FADE_MS = 200
INPUT_DETECTED_WAIT = 2.5
FOCUS_TRIES = 10
FOCUS_WAIT_MS = 50

# actions that are not a key press: mouse moves and Kodi's own idle actions
NOT_INPUT = (0, 107, 999)
BACK_ACTIONS = (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK)

# a step's name and icon (stand-ins from the skin's media until drawn icons exist)
STEP_TITLES = {
    'remote': 32101,
    'language': 32157,
    'network': 32104,
    'timezone': 32009,
    'device': 32108,
    'ssh': 32004,
    'newsletter': 32112,
    'warranty': 32023,
    'license': 32010,
    'summary': 32115,
}
STEP_ICONS = {
    'remote': 'DefaultAddonPeripheral.png',
    'language': 'DefaultAddonLanguage.png',
    'network': 'DefaultNetwork.png',
    'timezone': 'DefaultCountry.png',
    'device': 'DefaultOSMC.png',
    'ssh': 'DefaultScript.png',
    'newsletter': 'DefaultUser.png',
    'warranty': 'DefaultFile.png',
    'license': 'DefaultFile.png',
    'summary': 'DefaultAddonsUpdates.png',
}

log = StandardLogger(ADDON_ID, os.path.basename(__file__)).log


def close_on_error(func):
    def wrapper(window, *args, **kwargs):
        try:
            return func(window, *args, **kwargs)
        except Exception:
            log(traceback.format_exc(), xbmc.LOGERROR)

    return wrapper


class SetupWindow(xbmcgui.WindowXMLDialog):

    def __init__(self, xml_filename, script_path, default_skin='Default', default_res='1080i',
                 state=None, lang=None):
        super(SetupWindow, self).__init__(xml_filename, script_path, default_skin, default_res)
        self.state = state
        self.lang = lang
        self.monitor = xbmc.Monitor()
        self.dialog = xbmcgui.Dialog()

        self.network = NetworkStep(lang, self.wifi_refreshed)

        self.mode = None
        self.rows = []  # the option rows' keys, in order
        self.picker = None  # (items [(label, value)], on_pick) while a list shows
        self.input_detected = False
        self.remote_watch = None

    # ---- Kodi callbacks ------------------------------------------------------------------

    def onInit(self):
        try:
            self.list_x = {OPTIONS: self.getControl(OPTIONS).getX(),
                           PICKER: self.getControl(PICKER).getX(),
                           SUMMARY: self.getControl(SUMMARY).getX()}
            self.show_step(fade=False)
        except Exception:
            # nothing can be shown: leave, rather than sit on an empty window
            log(traceback.format_exc(), xbmc.LOGERROR)
            self.state.failed = True
            self.close()

    @close_on_error
    def onClick(self, control_id):
        if control_id == BACK:
            self.go_back()
        elif control_id == DONE:
            self.go_done()
        elif control_id == OPTIONS:
            position = self.getControl(OPTIONS).getSelectedPosition()
            if 0 <= position < len(self.rows):
                self.option_clicked(self.rows[position])
        elif control_id == PICKER:
            position = self.getControl(PICKER).getSelectedPosition()
            if self.picker and 0 <= position < len(self.picker[0]):
                items, on_pick = self.picker
                self.close_picker(refresh=False)
                on_pick(items[position][1])

    @close_on_error
    def onAction(self, action):
        action_id = action.getId()

        if self.state.step == 'remote':
            if self.state.testing and action_id in BACK_ACTIONS:
                self.close()  # "Test walk through" can be left
                return
            # no key leaves setup or goes back here; any key counts as input
            if action_id not in NOT_INPUT and not self.input_detected:
                self.remote_input()
            return

        if action_id in BACK_ACTIONS:
            self.go_back()

    # ---- moving between steps ------------------------------------------------------------

    def go_back(self):
        if self.mode == 'picker':
            self.close_picker()
        elif self.mode == 'wired':
            self.network.wired = None  # discard
            self.show_step(fade=False)
        elif self.state.has_back():
            self.state.back()
            self.show_step()

    def go_done(self):
        if self.mode == 'wired':
            if self.network.apply_wired():
                self.monitor.waitForAbort(2)
            self.show_step(fade=False)
            return

        if self.state.step == 'summary':
            self.finish()
            return

        self.state.done()
        self.show_step()

    def show_step(self, fade=True, focus=None):
        if fade:
            self.setProperty('Setup.Changing', 'true')
            xbmc.sleep(FADE_MS)

        step = self.state.step
        self.picker = None
        self.setProperty('Setup.Step', step)
        self.setProperty('Setup.Title', self.lang(STEP_TITLES[step]))
        self.setProperty('Setup.Icon', STEP_ICONS[step])
        self.clearProperty('Setup.Help')
        self.clearProperty('Setup.Remote')

        # the clock shows once Timezone is done
        if self.state.position(self.state.furthest) > self.state.position('timezone'):
            self.setProperty('Setup.Clock', 'true')

        self.getControl(BACK).setLabel(self.lang(32117))
        self.getControl(DONE).setLabel(self.lang(32080) if step in ('warranty', 'license')
                                       else self.lang(32012) if step == 'summary'
                                       else self.lang(32118))
        self.getControl(BACK).setVisible(self.state.has_back())

        focus = getattr(self, 'render_' + step)() if focus is None else focus

        if fade:
            self.clearProperty('Setup.Changing')

        if focus:  # Remote has nothing to focus
            self.focus_control(focus)

    def set_mode(self, mode):
        self.mode = mode
        self.setProperty('Setup.Mode', mode)
        # no Done on Remote (which has no Back either), and only Back while a list shows;
        # Kodi's Python cannot reach the grouplist itself, so this hides the button
        self.getControl(DONE).setVisible(mode not in ('remote', 'picker'))

    def focus_control(self, control_id):
        """ Focuses a control, checking it took: a new mode's lists show a frame later, and
            after Remote, where nothing has focus, Kodi focuses the window's first control """
        for _ in range(FOCUS_TRIES):
            self.setFocusId(control_id)
            xbmc.sleep(FOCUS_WAIT_MS)
            try:
                if self.getFocusId() == control_id:
                    return
            except RuntimeError:  # nothing has focus yet
                pass
        log('Could not focus %d' % control_id)

    # ---- rows ----------------------------------------------------------------------------

    def set_rows(self, rows, control_id=OPTIONS, top=None):
        """ rows: [(key, label, value, kind, on, enabled)] """
        self.rows = [row[0] for row in rows] if control_id == OPTIONS else self.rows
        items = []
        for key, label, value, kind, on, enabled in rows:
            item = xbmcgui.ListItem(label, label2=value or '', offscreen=True)
            item.setProperty('kind', kind)
            item.setProperty('on', 'true' if on else '')
            item.setProperty('disabled', '' if enabled else 'true')
            items.append(item)

        control = self.getControl(control_id)
        control.reset()
        control.addItems(items)
        height = max(len(items), 1) * ROW_HEIGHT
        if top is None:
            top = LIST_MIDDLE - height // 2
        control.setPosition(self.list_x[control_id], top)
        control.setHeight(height)
        return top + height

    @staticmethod
    def row(key, label, value='', kind='button', on=False, enabled=True):
        return key, label, value, kind, on, enabled

    def option_clicked(self, key):
        if self.mode == 'wired':
            self.network.edit_wired(key)
            self.render_wired(focus_key=key)
            return
        handler = getattr(self, 'click_' + key, None)
        if handler:
            handler()
        else:
            log('No handler for %s on %s' % (key, self.state.step))

    def refocus(self, key):
        if key in self.rows:
            self.getControl(OPTIONS).selectItem(self.rows.index(key))
            self.focus_control(OPTIONS)

    # ---- lists in place ------------------------------------------------------------------

    def open_picker(self, items, current, on_pick):
        """ items: [(label, value)]; Back closes the list unchanged """
        self.picker = (items, on_pick)
        self.picker_return = self.rows[self.getControl(OPTIONS).getSelectedPosition()] \
            if self.rows else None
        self.set_mode('picker')

        control = self.getControl(PICKER)
        control.reset()
        control.addItems([xbmcgui.ListItem(label, offscreen=True) for label, _ in items])
        rows = min(len(items), PICKER_ROWS)
        control.setPosition(self.list_x[PICKER], LIST_MIDDLE - rows * ROW_HEIGHT // 2)
        control.setHeight(rows * ROW_HEIGHT)

        values = [value for _, value in items]
        if current in values:
            control.selectItem(values.index(current))
        self.focus_control(PICKER)

    def close_picker(self, refresh=True):
        self.picker = None
        key = self.picker_return
        if refresh:
            self.show_step(fade=False, focus=None)
            self.refocus(key)

    def picked(self, key):
        """ After a list closed on a choice: the step again, focus back on its row """
        self.show_step(fade=False)
        self.refocus(key)

    # ---- Remote --------------------------------------------------------------------------

    def render_remote(self):
        self.set_mode('remote')
        self.input_detected = False
        self.remote_text(system.is_remote_paired())

        if self.remote_watch is None:
            self.remote_watch = threading.Thread(target=self.watch_remote)
            self.remote_watch.daemon = True
            self.remote_watch.start()
        return None

    def remote_text(self, paired, detected=False):
        if paired:
            text = self.lang(32120) + '[CR][CR]' + self.lang(32122 if detected else 32121)
        else:
            text = self.lang(32119) + ('[CR][CR]' + self.lang(32122) if detected else '')
        self.setProperty('Setup.Remote', text)

    def watch_remote(self):
        """ Shows the paired text once the OSMC remote pairs; only sets a window property """
        paired = system.is_remote_paired()
        while self.state.step == 'remote' and not self.monitor.waitForAbort(1):
            now = system.is_remote_paired()
            if now != paired and not self.input_detected:
                paired = now
                self.remote_text(paired)
        self.remote_watch = None

    def remote_input(self):
        self.input_detected = True
        self.remote_text(system.is_remote_paired(), detected=True)
        if self.monitor.waitForAbort(INPUT_DETECTED_WAIT):
            return
        self.state.done()
        self.show_step()

    # ---- Language ------------------------------------------------------------------------

    def render_language(self):
        self.set_mode('options')
        self.setProperty('Setup.Help', self.lang(32123))

        label, addon_id = system.current_language()
        self.state.language, self.state.language_label = addon_id, label
        region = system.regional_setting('locale.country')
        self.state.region = system.label_of(region)

        self.set_rows([
            self.row('language', self.lang(32102), self.state.language_label),
            self.row('region', self.lang(32103), self.state.region),
        ])
        return DONE

    def click_language(self):
        def chosen(addon_id):
            if addon_id == self.state.language:
                self.picked('language')
                return
            # Kodi reloads its interface for a new language; setup reopens on this step
            self.state.pending_language = addon_id
            self.close()

        self.open_picker(system.languages(), self.state.language, chosen)

    def click_region(self):
        region = system.regional_setting('locale.country')

        def chosen(value):
            system.set_setting('locale.country', value)
            self.picked('region')

        self.open_picker(region['options'], region['value'], chosen)

    # ---- Network -------------------------------------------------------------------------

    def render_network(self):
        self.set_mode('options')
        help_text, wifi_value, wired_value, connection, online = self.network.status()
        self.state.connection = connection
        self.state.online = online
        self.setProperty('Setup.Help', help_text)

        rows = []
        if wifi_value:
            rows.append(self.row('wifi', self.lang(32105), wifi_value))
        rows.append(self.row('wired', self.lang(32106), wired_value))
        self.set_rows(rows)

        # offline, the step opens on Wi-Fi
        if connection == (None, None) and self.rows[0] == 'wifi':
            self.getControl(OPTIONS).selectItem(0)
            return OPTIONS
        return DONE

    def wifi_refreshed(self):
        if self.mode == 'picker' or self.state.step == 'network':
            self.show_step(fade=False)
            self.refocus('wifi')

    def click_wifi(self):
        self.open_picker(self.network.wifi_items(), None, self.wifi_chosen)

    def wifi_chosen(self, key):
        self.network.choose_wifi(key)
        self.picked('wifi')

    def click_wired(self):
        if not self.network.open_wired():
            return
        self.render_wired()

    def render_wired(self, focus_key='Method'):
        self.set_mode('wired')
        rows = [self.row(key, label, value, 'button' if enabled else 'readonly', enabled=enabled)
                for key, label, value, enabled in self.network.wired_rows()]
        self.set_rows(rows)
        self.refocus(focus_key)

    # ---- Timezone ------------------------------------------------------------------------

    def render_timezone(self):
        self.set_mode('options')

        if not self.state.timezone_detected:
            self.state.timezone_detected = True
            if self.state.online:
                countries = system.regional_setting('locale.timezonecountry')['options']
                country, timezone = system.detect_timezone(countries)
                if country:
                    system.set_timezone(country, timezone)
                    self.state.timezone_found = True

        # "were detected from the network connection" only when they were
        self.setProperty('Setup.Help', self.lang(32127 if self.state.timezone_found else 32163))

        settings = system.regional_settings()
        country = settings.get('locale.timezonecountry', {'value': '', 'options': []})
        timezone = settings.get('locale.timezone', {'value': '', 'options': []})
        self.state.timezone_country = system.label_of(country)
        self.state.timezone = system.label_of(timezone)

        self.set_rows([
            self.row('timezone_country', self.lang(32107), self.state.timezone_country),
            self.row('timezone', self.lang(32009), self.state.timezone),
        ])
        return DONE

    def click_timezone_country(self):
        country = system.regional_setting('locale.timezonecountry')

        def chosen(value):
            options, timezone = system.timezones(value)
            system.set_timezone(value, timezone)
            self.picked('timezone_country')

        self.open_picker(country['options'], country['value'], chosen)

    def click_timezone(self):
        timezone = system.regional_setting('locale.timezone')

        def chosen(value):
            system.set_timezone(system.regional_setting('locale.timezonecountry')['value'], value)
            self.picked('timezone')

        self.open_picker(timezone['options'], timezone['value'], chosen)

    # ---- Device name ---------------------------------------------------------------------

    def render_device(self):
        self.set_mode('options')
        self.setProperty('Setup.Help', self.lang(32128))
        self.set_rows([
            self.row('device_name', self.lang(32108), self.state.hostname),
            self.row('random_name', self.lang(32109)),
        ])
        return DONE

    def click_device_name(self):
        heading = self.lang(32108)
        name = self.state.hostname
        while True:
            keyboard = xbmc.Keyboard(name, heading)
            keyboard.doModal()
            if not keyboard.isConfirmed():
                return
            name = keyboard.getText().strip()
            problem = setup_answers.hostname_problem(name)
            if problem is None:
                break
            # the keyboard opens again, naming the broken rule
            heading = '%s: %s' % (self.lang(32108), self.lang({
                setup_answers.NAME_EMPTY: 32151,
                setup_answers.NAME_CHARACTERS: 32149,
                setup_answers.NAME_HYPHEN: 32148,
                setup_answers.NAME_LENGTH: 32150,
            }[problem]))

        self.state.hostname = name
        self.render_device()
        self.refocus('device_name')

    def click_random_name(self):
        self.state.hostname = setup_answers.random_name(self.state.hostname)
        self.render_device()
        self.refocus('random_name')

    # ---- SSH -----------------------------------------------------------------------------

    def render_ssh(self):
        self.set_mode('options')
        self.setProperty('Setup.Help', self.lang(32129))
        rows = [self.row('ssh_server', self.lang(32110), kind='switch', on=self.state.ssh)]
        if self.state.ssh:
            rows.append(self.row('ssh_password', self.lang(32111),
                                 self.lang(32146) if self.state.ssh_password else self.lang(32145)))
        self.set_rows(rows)
        return DONE

    def click_ssh_server(self):
        self.state.ssh = not self.state.ssh
        self.render_ssh()
        self.refocus('ssh_server')

    def click_ssh_password(self):
        first = self.dialog.input(self.lang(32158), option=xbmcgui.ALPHANUM_HIDE_INPUT)
        if not first:
            return
        second = self.dialog.input(self.lang(32159), option=xbmcgui.ALPHANUM_HIDE_INPUT)
        if not second:
            return
        if first != second:
            self.dialog.ok(self.lang(32160), self.lang(32161))  # the entries did not match
            return
        self.state.ssh_password = first
        self.render_ssh()
        self.refocus('ssh_password')

    # ---- Newsletter ----------------------------------------------------------------------

    def render_newsletter(self):
        self.set_mode('options')
        self.setProperty('Setup.Help', self.lang(32130))
        rows = [self.row('newsletter', self.lang(32113), kind='switch', on=self.state.newsletter)]
        if self.state.newsletter:
            rows.append(self.row('email', self.lang(32114), self.state.email))
        self.set_rows(rows)
        return DONE

    def ask_email(self):
        heading = self.lang(32162)
        address = self.state.email
        while True:
            address = self.dialog.input(heading, address, type=xbmcgui.INPUT_ALPHANUM)
            if not address:
                return None
            if setup_answers.is_email(address.strip()):
                return address.strip()
            heading = self.lang(32152)  # not an email address

    def click_newsletter(self):
        if self.state.newsletter:
            self.state.newsletter = False
        else:
            address = self.ask_email()
            if address:
                self.state.email = address
                self.state.newsletter = True
        self.render_newsletter()
        self.refocus('newsletter')

    def click_email(self):
        address = self.ask_email()
        if address:
            self.state.email = address
        self.render_newsletter()
        self.refocus('email')

    # ---- Warranty and License ------------------------------------------------------------

    def render_text(self, text):
        self.set_mode('text')
        self.rows = []
        self.getControl(TEXT).setText(text)
        return DONE

    def render_warranty(self):
        return self.render_text(legal_warranty.__warranty__)

    def render_license(self):
        return self.render_text(legal_license.__license__)

    # ---- Summary -------------------------------------------------------------------------

    def render_summary(self):
        self.set_mode('summary')
        answers = self.state.summary(self.lang)
        total = (len(answers) + 1) * ROW_HEIGHT
        top = LIST_MIDDLE - total // 2
        bottom = self.set_rows([self.row(str(n), title, choice, 'readonly')
                                for n, (title, choice) in enumerate(answers)],
                               control_id=SUMMARY, top=top)
        self.set_rows([self.row('check_updates', self.lang(32116), kind='switch',
                                on=self.state.check_updates)], top=bottom)
        return DONE

    def click_check_updates(self):
        self.state.check_updates = not self.state.check_updates
        self.render_summary()
        self.refocus('check_updates')

    def finish(self):
        """ Applies the device name and SSH, sends the newsletter address, marks setup done """
        state = self.state
        if state.testing:
            # "Test walk through": the device stays as it is
            state.finished = True
            self.close()
            return

        password_set = True
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        try:
            if state.hostname != state.original_hostname:
                system.set_hostname(state.hostname)
            if state.ssh != system.is_ssh_enabled():
                system.set_ssh(state.ssh)
            if state.ssh and state.ssh_password:
                password_set = system.set_password(state.ssh_password)
            if state.online and state.newsletter and state.email:
                system.subscribe_newsletter(state.email)
            system.mark_done()
        finally:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

        if not password_set:
            # 'SSH' 'The password could not be changed, so it stays as it was.'
            _ = self.dialog.ok(self.lang(STEP_TITLES['ssh']), self.lang(32164))

        state.finished = True
        self.close()
