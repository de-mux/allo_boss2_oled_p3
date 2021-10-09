#!/usr/bin/python
"""
Copyright 2020 allo.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from enum import auto, Enum, IntEnum
import logging
import os
import socket
import struct
import sys
import time

import fcntl
from Hardware.SH1106.SH1106LCD import SH1106LCD
from Hardware.I2CConfig import i2cConfig
import IRModule
import RPi.GPIO as GPIO

from alsa import AlsaMixerBoss2
from utils import shell_cmd

SPLASH_SCREEN_TIMEOUT = 5
DISPLAY_OFF_TIMEOUT = 30
LOG_FORMAT = "%(asctime)-15s [%(levelname)s] (%(name)s) %(message)s"
LOG_LEVEL = logging.INFO

IR_PIN = 16
SW1 = 14
SW2 = 15
SW3 = 23
SW4 = 8
SW5 = 24
RST = 12

h_name = "Allo"
A_CARD = "Boss2"
A_CARD1 = "BOSS2"
m_indx = 1
f_indx = 1
fil_sp = 0
de_emp = 0
non_os = 0
ph_comp = 0
hv_en = 0
hp_fil = 0
ok_flag = 0
bit_rate = 0
bit_format = 0
last_bit_format = 0
sec_flag = 0
irp = 0
irm = 0
ir1 = 0
irok = 0
ir3 = 0
ir4 = 0
ir5 = 0
display_next_timeout = None


class DisplayFlag(IntEnum):
    OFF = 0
    ON = 1
    TURN_OFF = 2
    TURN_ON = 3


display_flag = DisplayFlag.OFF

lcd = None

logger = logging.getLogger("Boss2")


def remote_callback(code):
    global irp
    global irm
    global ir1
    global irok
    global ir3
    global ir4
    global ir5
    logger.debug("Remote callback: 0x{}".format(hex(code)))
    if code == 0xC77807F:
        irp = 1
        reset_display_timeout()
    elif code == 0xC7740BF:
        irm = 1
        reset_display_timeout()
    elif code == 0xC77906F:
        ir1 = 1
        reset_display_timeout()
    elif code == 0xC7730CF:
        irok = 1
        reset_display_timeout()
    elif code == 0xC7720DF:
        ir3 = 1
        reset_display_timeout()
    elif code == 0xC77A05F:
        ir4 = 1
        reset_display_timeout()
    elif code == 0xC7710EF:
        ir5 = 1
        reset_display_timeout()
    return


class FrontPanelInterface:
    def __init__(self):
        self._switches = {
            Switch.LEFT: SW1,
            Switch.OK: SW2,
            Switch.UP: SW3,
            Switch.DOWN: SW4,
            Switch.RIGHT: SW5,
        }

    def get_switch_state(self):
        state = {switch_id: 0 for switch_id in self._switches}

        for switch_id, pin in self._switches.items():
            if GPIO.input(pin) != GPIO.HIGH:
                state[switch_id] = 1
        return state


class Screen(IntEnum):
    INFO = 0
    VOL = 0
    MENU = 1
    BOOT = 2
    FILTER = 3
    HV = 4
    SP = 5
    HP = 6
    DE_EMPHASIS = 7
    NON_OSAMP = 8
    PHASE_COMPENSATION = 9


class Switch(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    OK = auto()


class GUI:
    def __init__(self, lcd, alsa_interface):
        self.lcd = lcd
        self.alsa = alsa_interface
        self.screen = Screen.INFO
        self.fp_interface = FrontPanelInterface()
        self._ip_lan = ""
        self._ip_wan = ""
        self._hostname = ""
        self._scr0_ref_count = 0
        # self._LED_FLAG = 0

    def display_splash(self):
        lcd.display_off()
        self._ip_lan = get_ip_address("eth0")
        self._ip_wan = get_ip_address("wlan0")
        h_name = "HOST:%s" % socket.gethostname()
        lcd.displayStringNumber(self._ip_lan, 0, 0)
        lcd.displayStringNumber(self._ip_wan, 6, 0)
        lcd.displayString(h_name, 2, 0)
        lcd.displayString(A_CARD1, 4, 0)
        lcd.display_on()
        time.sleep(SPLASH_SCREEN_TIMEOUT)
        lcd.clearScreen(keep_display_off=True)

    def display_err(self, msg):
        col = int(self.lcd.COLUMNS / 2 - len(msg) / 2)
        lcd.displayString(msg, row=4, col=col)
        lcd.displayStringNumber(self._ip_lan, 0, 0)
        lcd.displayStringNumber(self._ip_wan, 6, 0)

    def _check_switches(self):
        return self.fp_interface.get_switch_state()

    def _volume_up(self):
        alsa_cvol, _, _ = self.alsa.getVol()
        alsa_hvol = alsa_cvol
        if alsa_hvol < 255 and alsa_hvol >= 240:
            alsa_hvol += 1
        if alsa_hvol < 240 and alsa_hvol >= 210:
            alsa_hvol += 3
        if alsa_hvol < 210 and alsa_hvol >= 120:
            alsa_hvol += 10
        if alsa_hvol < 120 and alsa_hvol >= 0:
            alsa_hvol += 30
        self.alsa.setVol(alsa_hvol)

    def _volume_down(self):
        alsa_cvol, _, _ = self.alsa.getVol()
        alsa_hvol = alsa_cvol
        if alsa_hvol <= 255 and alsa_hvol > 240:
            alsa_hvol -= 1
        if alsa_hvol <= 240 and alsa_hvol > 210:
            alsa_hvol -= 3
        if alsa_hvol <= 210 and alsa_hvol > 120:
            alsa_hvol -= 10
        if alsa_hvol <= 120 and alsa_hvol > 0:
            alsa_hvol -= 30
        self.alsa.setVol(alsa_hvol)

    def _check_display_timeout(self):
        global display_next_timeout
        global display_flag

        if time.time() >= display_next_timeout and display_flag != DisplayFlag.OFF:
            display_flag = DisplayFlag.TURN_OFF

        if display_flag == DisplayFlag.TURN_OFF:
            logger.debug("Display OFF")
            self.lcd.display_off()
            display_flag = DisplayFlag.OFF
        elif display_flag == DisplayFlag.TURN_ON:
            logger.debug("Display ON")
            self.lcd.display_on()
            display_flag = DisplayFlag.ON

    def do_update(self):
        global m_indx
        global h_name
        global alsa_cvol
        global f_indx
        global fil_sp
        global hp_fil
        global de_emp
        global ph_comp
        global non_os
        global hv_en
        global ok_flag
        global filter_mod
        global mute
        global sec_flag
        global irm
        global irok
        global ir1
        global ir3
        global ir4
        global ir5

        self._check_display_timeout()

        if self._scr0_ref_count < 10:
            self._scr0_ref_count += 1
            time.sleep(0.02)
        else:
            sec_flag = 1
            self._scr0_ref_count = 0

        switches = self._check_switches()
        if any(switches.values()):
            reset_display_timeout()

        if switches[Switch.LEFT] == 1 or ir1 == 1:
            time.sleep(0.1)
            ir1 = 0
            if self.screen == Screen.INFO:
                self.lcd.clearScreen()
                self.menuScr()
            elif self.screen == Screen.MENU:
                self.screenVol()
            elif self.screen == Screen.BOOT:
                self.menuScr()
            elif self.screen == Screen.FILTER:
                self.menuScr()
            elif self.screen == Screen.HV:
                if hv_en == 0:
                    hv_en = 1
                    self.hvScr4()
            elif self.screen == Screen.SP:
                if fil_sp == 0:
                    fil_sp = 1
                    self.spScr5()
            elif self.screen == Screen.HP:
                if hp_fil == 0:
                    hp_fil = 1
                    self.hpScr6()
            elif self.screen == Screen.DE_EMPHASIS:
                if de_emp == 0:
                    de_emp = 1
                    self.deScr7()
            elif self.screen == Screen.NON_OSAMP:
                if non_os == 0:
                    non_os = 1
                    self.nonScr8()
            elif self.screen == Screen.PHASE_COMPENSATION:
                if ph_comp == 0:
                    ph_comp = 1
                    self.phScr9()
            else:
                logger.error("Invalid screen: {}".format(self.screen))

        if irm == 1:
            time.sleep(0.1)
            sec_flag = 1
            irm = 0
            mute = self.alsa.getMuteStatus(self.alsa.CONTROL.MA_CTRL)
            if mute == 0:
                self.alsa.setMuteStatus(self.alsa.CONTROL.MA_CTRL, 1)
                self.alsa.setMuteStatus(self.alsa.CONTROL.DIG_CTRL, 1)
            else:
                self.alsa.setMuteStatus(self.alsa.CONTROL.MA_CTRL, 0)
                self.alsa.setMuteStatus(self.alsa.CONTROL.DIG_CTRL, 0)

        if switches[Switch.OK] == 1 or irok == 1:
            time.sleep(0.1)
            irm_nflag = 0
            if irok == 1:
                irm_nflag = 1
                irok = 0
            if self.screen == Screen.INFO and irm_nflag == 0:
                sec_flag = 1
                mute = self.alsa.getMuteStatus(self.alsa.CONTROL.MA_CTRL)
                if mute == 0:
                    self.alsa.setMuteStatus(self.alsa.CONTROL.MA_CTRL, 1)
                    self.alsa.setMuteStatus(self.alsa.CONTROL.DIG_CTRL, 1)
                else:
                    self.alsa.setMuteStatus(self.alsa.CONTROL.MA_CTRL, 0)
                    self.alsa.setMuteStatus(self.alsa.CONTROL.DIG_CTRL, 0)
            elif self.screen == Screen.MENU:
                if m_indx == 1:
                    self.bootScr()
                elif m_indx == 2:
                    self.hvScr4()
                elif m_indx == 3:
                    self.filtScr()
                elif m_indx == 4:
                    self.spScr5()
            elif self.screen == Screen.BOOT:
                self.menuScr()
            elif self.screen == Screen.FILTER:
                if f_indx == 1:
                    self.phScr9()
                elif f_indx == 2:
                    self.hpScr6()
                elif f_indx == 3:
                    self.deScr7()
                elif f_indx == 4:
                    self.nonScr8()
            elif self.screen == Screen.HV:
                ok_flag = 0
                mute = self.alsa.getMuteStatus(self.alsa.CONTROL.HV_CTRL)
                if mute != hv_en:
                    self.alsa.setMuteStatus(self.alsa.CONTROL.HV_CTRL, hv_en)
                self.menuScr()
            elif self.screen == Screen.SP:
                ok_flag = 0
                filter_cur = self.alsa.getFilterStatus()
                if filter_cur != fil_sp:
                    self.alsa.setFilterStatus(fil_sp)
                self.menuScr()
            elif self.screen == Screen.HP:
                ok_flag = 0
                mute = self.alsa.getMuteStatus(self.alsa.CONTROL.HP_CTRL)
                if mute != hp_fil:
                    self.alsa.setMuteStatus(self.alsa.CONTROL.HP_CTRL, hp_fil)
                self.filtScr()
            elif self.screen == Screen.DE_EMPHASIS:
                ok_flag = 0
                mute = self.alsa.getMuteStatus(self.alsa.CONTROL.DE_CTRL)
                if mute != de_emp:
                    self.alsa.setMuteStatus(self.alsa.CONTROL.DE_CTRL, de_emp)
                self.filtScr()
            elif self.screen == Screen.NON_OSAMP:
                ok_flag = 0
                mute = self.alsa.getMuteStatus(self.alsa.CONTROL.NON_CTRL)
                if mute != non_os:
                    self.alsa.setMuteStatus(self.alsa.CONTROL.NON_CTRL, non_os)
                self.filtScr()
            elif self.screen == Screen.PHASE_COMPENSATION:
                ok_flag = 0
                mute = self.alsa.getMuteStatus(self.alsa.CONTROL.PH_CTRL)
                if mute != ph_comp:
                    self.alsa.setMuteStatus(self.alsa.CONTROL.PH_CTRL, ph_comp)
                self.filtScr()

        if switches[Switch.UP] == 1 or ir3 == 1:
            time.sleep(0.1)
            ir3 = 0
            if self.screen == Screen.INFO:
                self._volume_up()
                self.screenVol()
            elif self.screen == Screen.MENU:
                if m_indx > 1:
                    m_indx -= 1
                self.menuScr()
            elif self.screen == Screen.FILTER:
                if f_indx > 1:
                    f_indx -= 1
                self.filtScr()

        if switches[Switch.DOWN] == 1 or ir4 == 1:
            time.sleep(0.1)
            ir4 = 0
            if self.screen == Screen.INFO:
                self._volume_down()
                self.screenVol()
            elif self.screen == Screen.MENU:
                m_indx += 1
                if m_indx > 4:
                    m_indx = 1
                self.menuScr()
            elif self.screen == Screen.FILTER:
                f_indx += 1
                if f_indx > 4:
                    f_indx = 1
                self.filtScr()
            elif self.screen == Screen.HV:
                if ok_flag == 0:
                    ok_flag = 1
                self.hvScr4()
            elif self.screen == Screen.SP:
                if ok_flag == 0:
                    ok_flag = 1
                self.spScr5()
            elif self.screen == Screen.HP:
                if ok_flag == 0:
                    ok_flag = 1
                self.self.hpScr6()
            elif self.screen == Screen.DE_EMPHASIS:
                if ok_flag == 0:
                    ok_flag = 1
                self.self.deScr7()
            elif self.screen == Screen.NON_OSAMP:
                if ok_flag == 0:
                    ok_flag = 1
                self.self.nonScr8()
            elif self.screen == Screen.PHASE_COMPENSATION:
                if ok_flag == 0:
                    ok_flag = 1
                self.self.phScr9()

        if switches[Switch.RIGHT] == 1 or ir5 == 1:
            time.sleep(0.1)
            ir5 = 0
            if self.screen == Screen.INFO:
                self.lcd.clearScreen()
                self.menuScr()
            elif self.screen == Screen.MENU:
                self.screenVol()
            elif self.screen == Screen.BOOT:
                self.menuScr()
            elif self.screen == Screen.FILTER:
                self.menuScr()
            elif self.screen == Screen.HV:
                if hv_en == 1:
                    hv_en = 0
                self.hvScr4()
            elif self.screen == Screen.SP:
                if fil_sp == 1:
                    fil_sp = 0
                self.spScr5()
            elif self.screen == Screen.HP:
                if hp_fil == 1:
                    hp_fil = 0
                self.hpScr6()
            elif self.screen == Screen.DE_EMPHASIS:
                if de_emp == 1:
                    de_emp = 0
                self.deScr7()
            elif self.screen == Screen.NON_OSAMP:
                if non_os == 1:
                    non_os = 0
                self.nonScr8()
            elif self.screen == Screen.PHASE_COMPENSATION:
                if ph_comp == 1:
                    ph_comp = 0
                self.phScr9()

        if sec_flag == 1:
            if self.screen == Screen.INFO:
                self.screenVol()
                sec_flag = 0

    def infoScr(self):
        if self.screen != Screen.INFO:
            self.screen = Screen.INFO
            lcd.clearScreen()

        lcd.displayString("VOL", 1, 0)
        lcd.displayString("0.0dB", 1, 60)
        lcd.displayString("PCM/DSD", 3, 0)
        lcd.displayString("SR", 5, 0)
        lcd.displayString("44.1kHz", 5, 60)

    def menuScr(self):
        global m_indx
        if self.screen != Screen.MENU:
            self.screen = Screen.MENU
            lcd.clearScreen()
        if m_indx == 1:
            lcd.displayInvertedString("SYSINFO", 0, 0)
        else:
            lcd.displayString("SYSINFO", 0, 0)
        if m_indx == 2:
            if hv_en == 0:
                lcd.displayInvertedString("HV-EN OFF", 2, 0)
            else:
                lcd.displayInvertedString("HV-EN ON", 2, 0)
        else:
            if hv_en == 0:
                lcd.displayString("HV-EN OFF", 2, 0)
            else:
                lcd.displayString("HV-EN ON", 2, 0)
        if m_indx == 3:
            lcd.displayInvertedString("FILTER", 4, 0)
        else:
            lcd.displayString("FILTER", 4, 0)
        if m_indx == 4:
            if fil_sp == 1:
                lcd.displayInvertedString("F-SPEED-FAS", 6, 0)
            else:
                lcd.displayInvertedString("F-SPEED-SLO", 6, 0)
        else:
            if fil_sp == 1:
                lcd.displayString("F-SPEED-FAS", 6, 0)
            else:
                lcd.displayString("F-SPEED-SLO", 6, 0)

    def bootScr(self):
        if self.screen != Screen.BOOT:
            self.screen = Screen.BOOT
            lcd.clearScreen()
        lcd.clearScreen()
        self._ip_lan = get_ip_address("eth0")
        self._ip_wan = get_ip_address("wlan0")
        lcd.displayString(A_CARD1, 0, 0)
        lcd.displayStringNumber(self._ip_lan, 2, 0)
        lcd.displayString(h_name, 4, 0)
        lcd.displayStringNumber(self._ip_wan, 6, 0)

    def filtScr(self):
        global fil_sp
        global hp_fil
        global de_emp
        global non_os
        global ph_comp
        global f_indx
        if self.screen != Screen.FILTER:
            self.screen = Screen.FILTER
            lcd.clearScreen()
        if f_indx == 1:
            lcd.displayInvertedString("PHCOMP ", 0, 5)
            lcd.displayInvertedString("| ", 0, 64)
            if ph_comp == 0:
                lcd.displayInvertedString("DIS", 0, 80)
            else:
                lcd.displayInvertedString("EN", 0, 80)
        else:
            lcd.displayString("PHCOMP ", 0, 5)
            lcd.displayString("| ", 0, 64)
            if ph_comp == 0:
                lcd.displayString("DIS", 0, 80)
            else:
                lcd.displayString("EN", 0, 80)

        if f_indx == 2:
            lcd.displayInvertedString("HP-FIL ", 2, 5)
            lcd.displayInvertedString("| ", 2, 64)
            if hp_fil == 0:
                lcd.displayInvertedString("DIS", 2, 80)
            else:
                lcd.displayInvertedString("EN", 2, 80)
        else:
            lcd.displayString("HP-FIL ", 2, 5)
            lcd.displayString("| ", 2, 64)
            if hp_fil == 0:
                lcd.displayString("DIS", 2, 80)
            else:
                lcd.displayString("EN", 2, 80)
        if f_indx == 3:
            lcd.displayInvertedString("DE-EMP ", 4, 5)
            lcd.displayInvertedString("| ", 4, 64)
            if de_emp == 0:
                lcd.displayInvertedString("DIS", 4, 80)
            else:
                lcd.displayInvertedString("EN", 4, 80)
        else:
            lcd.displayString("DE-EMP ", 4, 5)
            lcd.displayString("| ", 4, 64)
            if de_emp == 0:
                lcd.displayString("DIS", 4, 80)
            else:
                lcd.displayString("EN", 4, 80)
        if f_indx == 4:
            lcd.displayInvertedString("NON-OS ", 6, 5)
            lcd.displayInvertedString("| ", 6, 64)
            if non_os == 0:
                lcd.displayInvertedString("DIS", 6, 80)
            else:
                lcd.displayInvertedString("EN", 6, 80)
        else:
            lcd.displayString("NON-OS ", 6, 5)
            lcd.displayString("| ", 6, 64)
            if non_os == 0:
                lcd.displayString("DIS", 6, 80)
            else:
                lcd.displayString("EN", 6, 80)

    def hvScr4(self):
        global hv_en
        global ok_flag
        if self.screen != Screen.HV:
            self.screen = Screen.HV
            lcd.clearScreen()
        lcd.displayString("HV ENABLE", 0, 20)
        if hv_en == 0:
            lcd.displayString("ON", 3, 20)
            lcd.displayInvertedString("OFF", 3, 70)
        else:
            lcd.displayInvertedString("ON", 3, 20)
            lcd.displayString("OFF", 3, 70)
        if ok_flag == 1:
            lcd.displayInvertedString("OK", 6, 50)
        else:
            lcd.displayString("OK", 6, 50)

    def spScr5(self):
        global fil_sp
        global ok_flag
        if self.screen != Screen.SP:
            self.screen = Screen.SP
            lcd.clearScreen()
        lcd.displayString("FILTER SPEED", 0, 5)
        if fil_sp == 0:
            lcd.displayString("FAST", 3, 10)
            lcd.displayInvertedString("SLOW", 3, 80)
        else:
            lcd.displayInvertedString("FAST", 3, 10)
            lcd.displayString("SLOW", 3, 80)
        if ok_flag == 1:
            lcd.displayInvertedString("OK", 6, 50)
        else:
            lcd.displayString("OK", 6, 50)

    def hpScr6(self):
        global ok_flag
        global hp_fil
        if self.screen != Screen.HP:
            self.screen = Screen.HP
            lcd.clearScreen()
        lcd.displayString("HP-FILT", 0, 20)
        if hp_fil == 0:
            lcd.displayString("EN", 3, 10)
            lcd.displayInvertedString("DIS", 3, 70)
        else:
            lcd.displayInvertedString("EN", 3, 10)
            lcd.displayString("DIS", 3, 70)
        if ok_flag == 1:
            lcd.displayInvertedString("OK", 6, 50)
        else:
            lcd.displayString("OK", 6, 50)

    def deScr7(self):
        global de_emp
        global ok_flag
        if self.screen != Screen.DE_EMPHASIS:
            self.screen = Screen.DE_EMPHASIS
            lcd.clearScreen()
        lcd.displayString("DE-EMPH", 0, 20)
        if de_emp == 0:
            lcd.displayString("EN", 3, 10)
            lcd.displayInvertedString("DIS", 3, 70)
        else:
            lcd.displayInvertedString("EN", 3, 10)
            lcd.displayString("DIS", 3, 70)
        if ok_flag == 1:
            lcd.displayInvertedString("OK", 6, 50)
        else:
            lcd.displayString("OK", 6, 50)

    def nonScr8(self):
        global non_os
        global ok_flag
        if self.screen != Screen.NON_OSAMP:
            self.screen = Screen.NON_OSAMP
            lcd.clearScreen()
        lcd.displayString("NON-OSAMP", 0, 20)
        if non_os == 0:
            lcd.displayString("EN", 3, 10)
            lcd.displayInvertedString("DIS", 3, 70)
        else:
            lcd.displayInvertedString("EN", 3, 10)
            lcd.displayString("DIS", 3, 70)
        if ok_flag == 1:
            lcd.displayInvertedString("OK", 6, 50)
        else:
            lcd.displayString("OK", 6, 50)

    def phScr9(self):
        global ph_comp
        global ok_flag
        if self.screen != Screen.PHASE_COMPENSATION:
            self.screen = Screen.PHASE_COMPENSATION
            lcd.clearScreen()
        lcd.displayString("PHA-COMP", 0, 20)
        if ph_comp == 0:
            lcd.displayString("EN", 3, 10)
            lcd.displayInvertedString("DIS", 3, 70)
        else:
            lcd.displayInvertedString("EN", 3, 10)
            lcd.displayString("DIS", 3, 70)
        if ok_flag == 1:
            lcd.displayInvertedString("OK", 6, 50)
        else:
            lcd.displayString("OK", 6, 50)

    def screenVol(self):
        global bit_rate
        global bit_format
        global last_bit_format
        if self.screen != Screen.INFO:
            self.screen = Screen.INFO
            lcd.clearScreen()

        _, left_db, _ = self.alsa.getVol()
        alsa_vol = "{:.2f}dB".format(left_db)
        if left_db == 0.0:
            lcd.displayString("    ", 1, 80)
        elif left_db > -10.0:
            lcd.displayString("    ", 1, 90)
        elif left_db > -100.0:
            lcd.displayString("  ", 1, 100)
        lcd.displayString(alsa_vol, 1, 20)
        mute = self.alsa.getMuteStatus(self.alsa.CONTROL.MA_CTRL)
        if mute == 0:
            lcd.displayString("@", 3, 50)
        else:
            lcd.displayString("  ", 3, 50)
        hw_format, hw_rate_num = self.alsa.getHwparam()

        # display hw info
        if hw_format == "S24_LE":
            bit_rate = "24"
            bit_format = hw_rate_num
            bit_format1 = str(bit_format)
            lcd.displayString(bit_rate, 5, 15)
            lcd.displayString("S", 5, 5)
            if last_bit_format != bit_format1:
                lcd.displayString("        ", 5, 50)
                last_bit_format = bit_format1
            lcd.displayString(bit_format1, 5, 50)
            reset_display_timeout()
        elif hw_format == "S32_LE":
            bit_rate = "32"
            bit_format = hw_rate_num
            bit_format1 = str(bit_format)
            lcd.displayString(bit_rate, 5, 15)
            lcd.displayString("S", 5, 5)
            if last_bit_format != bit_format1:
                lcd.displayString("        ", 5, 50)
                last_bit_format = bit_format1
            lcd.displayString(bit_format1, 5, 50)
            reset_display_timeout()
        elif hw_format == "S16_LE":
            bit_rate = "16"
            bit_format = hw_rate_num
            bit_format1 = str(bit_format)
            lcd.displayString(bit_rate, 5, 15)
            lcd.displayString("S", 5, 5)
            if last_bit_format != bit_format1:
                lcd.displayString("        ", 5, 50)
                last_bit_format = bit_format1
            lcd.displayString(bit_format1, 5, 50)
            reset_display_timeout()
        else:
            bit_rate = "closed"
            lcd.displayStringNumber("   ", 5, 15)
            lcd.displayString(" ", 5, 5)
            lcd.displayString("        ", 5, 50)
            last_bit_format = 0


def getCardNumber():
    setflag = 0
    stdout, _ = shell_cmd(["aplay", "-l"])
    line_str = stdout.split("\n")
    for line in line_str:
        if A_CARD in line:
            setflag = 1
            word_str = line.split()
            card = word_str[1]
            card_number = card[0]
            break
    if setflag == 0:
        logger.error("No Boss2")
        return None
    else:
        return card_number


def get_ip_address(ifname):
    ip_address = ""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        ip_address = socket.inet_ntoa(
            fcntl.ioctl(s.fileno(), 0x8915, struct.pack("256s", ifname[:15]))[20:24]
        )
    except Exception:
        pass

    try:
        out, _ = shell_cmd(["ip", "addr", "show", ifname])
        ip_address = out.split("inet ")[1].split("/")[0]
    except Exception as err:
        logger.warning("Unable to obtain IP address for {} -- {}".format(ifname, err))
        ip_address = "{}: NA".format(ifname)
    return ip_address


def init_gpio(mode=GPIO.BOARD):
    GPIO.setwarnings(False)
    GPIO.setmode(mode)
    GPIO.setup(SW1, GPIO.IN)
    GPIO.setup(SW2, GPIO.IN)
    GPIO.setup(SW3, GPIO.IN)
    GPIO.setup(SW4, GPIO.IN)
    GPIO.setup(SW5, GPIO.IN)
    GPIO.setup(IR_PIN, GPIO.IN)
    time.sleep(0.1)


def init_gpio_bcm():
    init_gpio(mode=GPIO.BCM)


def gpio_cleanup():
    GPIO.cleanup(IR_PIN)
    GPIO.cleanup(SW1)
    GPIO.cleanup(SW2)
    GPIO.cleanup(SW3)
    GPIO.cleanup(SW4)
    GPIO.cleanup(SW5)


def reset_display_timeout():
    global display_flag
    global display_next_timeout

    display_next_timeout = time.time() + DISPLAY_OFF_TIMEOUT
    if display_flag != DisplayFlag.ON:
        display_flag = DisplayFlag.TURN_ON
    logger.debug("Display timeout reset +{}s".format(DISPLAY_OFF_TIMEOUT))


def shutdown_lcd(lcd):
    try:
        lcd.display_off()
        lcd.clearScreen()
    except Exception as err:
        logger.warning("Unable to clear LCD: {}".format(err))


def main():
    global h_name
    global lcd

    logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
    if os.name != "posix":
        sys.exit("platform not supported")
    reset_display_timeout()
    i2cConfig()
    lcd = SH1106LCD()

    card_num = getCardNumber()
    alsa_boss2 = AlsaMixerBoss2(card_num, A_CARD1)
    gui = GUI(lcd, alsa_boss2)
    gui.display_splash()

    if card_num is None:
        logger.error("No card detected")
        gui.display_err("NO BOSS2")
        exit(0)

    time.sleep(0.04)
    ir = IRModule.IRRemote(callback="DECODE")

    init_gpio_bcm()

    GPIO.add_event_detect(IR_PIN, GPIO.BOTH, callback=ir.pWidth)
    logger.debug("Setting up IR callback")
    ir.set_callback(remote_callback)
    ir.set_repeat(True)

    try:
        gui.screenVol()
        hp_fil, hv_en, non_os, ph_comp, de_emp, fil_sp = alsa_boss2.update_status()
        while True:
            gui.do_update()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        logger.info("Cleaning up...")
        if lcd:
            shutdown_lcd(lcd)
        ir.remove_callback()
        gpio_cleanup()


if __name__ == "__main__":
    main()
