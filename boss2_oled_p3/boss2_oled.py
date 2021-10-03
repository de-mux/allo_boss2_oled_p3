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

import os
import sys
import RPi.GPIO as GPIO
import time
import subprocess

if os.name != "posix":
    sys.exit("platform not supported")
import socket
import fcntl
import struct
from Hardware.SH1106.SH1106LCD import SH1106LCD
from Hardware.I2CConfig import i2cConfig
import IRModule


SUBPROCESS_TIMEOUT = 30
SPLASH_SCREEN_TIMEOUT = 5

IR_PIN = 16
SW1 = 14
SW2 = 15
SW3 = 23
SW4 = 8
SW5 = 24
RST = 12

DE_CTRL = "PCM De-emphasis Filter"
HP_CTRL = "PCM High-pass Filter"
PH_CTRL = "PCM Phase Compensation"
NON_CTRL = "PCM Nonoversample Emulate"
HV_CTRL = "HV_Enable"
SP_CTRL = "PCM Filter Speed"
MA_CTRL = "Master"
DIG_CTRL = "Digital"

h_name = "Allo"
A_CARD = "Boss2"
A_CARD1 = "BOSS2"
m_indx = 1
f_indx = 1
alsa_hvol = 230
alsa_cvol = 230
fil_sp = 0
de_emp = 0
non_os = 0
ph_comp = 0
hv_en = 0
hp_fil = 0
ok_flag = 0
card_num = 0
bit_rate = 0
bit_format = 0
last_bit_format = 0
mute = 1
sec_flag = 0
# status_M = 0
update_M = 0
# filter_cur = 0
filter_mod = 0
bs1 = 0
bs2 = 0
bs3 = 0
bs4 = 0
bs5 = 0
irp = 0
irm = 0
ir1 = 0
irok = 0
ir3 = 0
ir4 = 0
ir5 = 0
led_off_counter = 0

lcd = None


def remote_callback(code):
    global irp
    global irm
    global ir1
    global irok
    global ir3
    global ir4
    global ir5
    global led_off_counter
    if code == 0xC77807F:
        irp = 1
        led_off_counter = 0
    elif code == 0xC7740BF:
        irm = 1
        led_off_counter = 0
    elif code == 0xC77906F:
        ir1 = 1
        led_off_counter = 0
    elif code == 0xC7730CF:
        irok = 1
        led_off_counter = 0
    elif code == 0xC7720DF:
        ir3 = 1
        led_off_counter = 0
    elif code == 0xC77A05F:
        ir4 = 1
        led_off_counter = 0
    elif code == 0xC7710EF:
        ir5 = 1
        led_off_counter = 0
    return


def volTimer():
    global sec_flag
    while True:
        time.sleep(1)
        sec_flag = 1


def update_status():

    global mute
    global hp_fil
    global hv_en
    global non_os
    global ph_comp
    global de_emp
    global fil_sp

    mute = getMuteStatus(MA_CTRL)
    hp_fil = getMuteStatus(HP_CTRL)
    hv_en = getMuteStatus(HV_CTRL)
    non_os = getMuteStatus(NON_CTRL)
    ph_comp = getMuteStatus(PH_CTRL)
    de_emp = getMuteStatus(DE_CTRL)
    fil_sp = getFilterStatus()


class GUI:
    def __init__(self, lcd):
        self._scr0_ref_count = 0
        self._LED_FLAG = 0
        self.lcd = lcd
        self.scr_num = 0

    def do_update(self):
        global m_indx
        # global w_ip
        global h_name
        global alsa_hvol
        global alsa_cvol
        global f_indx
        global fil_sp
        global hp_fil
        global de_emp
        global ph_comp
        global non_os
        global hv_en
        global ok_flag
        global update_M
        global filter_mod
        global mute
        global sec_flag
        global bs1
        global bs2
        global bs3
        global bs4
        global bs5
        global irm
        global irok
        global ir1
        global ir3
        global ir4
        global ir5
        global led_off_counter

        if led_off_counter == 950:
            self._LED_FLAG = 1
        elif led_off_counter == 1:
            self._LED_FLAG = 0

        if led_off_counter > 950:
            led_off_counter = 951

        if self._LED_FLAG == 1:
            self.lcd.display_off()
            self._LED_FLAG = 2
        elif self._LED_FLAG == 0:
            self.lcd.display_on()
            self._LED_FLAG = 2

        if self._scr0_ref_count < 10:
            self._scr0_ref_count += 1
            time.sleep(0.02)
        else:
            sec_flag = 1
            self._scr0_ref_count = 0

        if GPIO.input(SW1) == GPIO.HIGH:
            time.sleep(0.04)
        else:
            time.sleep(0.04)
            bs1 = 1
            led_off_counter = 0

        if GPIO.input(SW2) == GPIO.HIGH:
            time.sleep(0.04)
        else:
            time.sleep(0.04)
            bs2 = 1
            led_off_counter = 0

        if GPIO.input(SW3) == GPIO.HIGH:
            time.sleep(0.04)
        else:
            time.sleep(0.04)
            bs3 = 1
            led_off_counter = 0

        if GPIO.input(SW4) == GPIO.HIGH:
            time.sleep(0.04)
        else:
            time.sleep(0.04)
            bs4 = 1
            led_off_counter = 0

        if GPIO.input(SW5) == GPIO.HIGH:
            time.sleep(0.04)
        else:
            time.sleep(0.04)
            bs5 = 1
            led_off_counter = 0

        if bs1 == 1 or ir1 == 1:
            time.sleep(0.1)
            bs1 = 0
            ir1 = 0
            if self.scr_num == 0:
                self.lcd.clearScreen()
                self.menuScr()
            elif self.scr_num == 1:
                self.screenVol()
            elif self.scr_num == 2:
                self.menuScr()
            elif self.scr_num == 3:
                self.menuScr()
            elif self.scr_num == 4:
                if hv_en == 0:
                    hv_en = 1
                    self.hvScr4()
            elif self.scr_num == 5:
                if fil_sp == 0:
                    fil_sp = 1
                    self.spScr5()
            elif self.scr_num == 6:
                if hp_fil == 0:
                    hp_fil = 1
                    self.hpScr6()
            elif self.scr_num == 7:
                if de_emp == 0:
                    de_emp = 1
                    self.deScr7()
            elif self.scr_num == 8:
                if non_os == 0:
                    non_os = 1
                    self.nonScr8()
            elif self.scr_num == 9:
                if ph_comp == 0:
                    ph_comp = 1
                    self.phScr9()
            else:
                print(self.scr_num)

        if irm == 1:
            time.sleep(0.1)
            sec_flag = 1
            irm = 0
            mute = getMuteStatus(MA_CTRL)
            if mute == 0:
                update_M = 1
                setMuteStatus(MA_CTRL)
                setMuteStatus(DIG_CTRL)
            else:
                update_M = 0
                setMuteStatus(MA_CTRL)
                setMuteStatus(DIG_CTRL)

        if bs2 == 1 or irok == 1:
            time.sleep(0.1)
            bs2 = 0
            irm_nflag = 0
            if irok == 1:
                irm_nflag = 1
                irok = 0
            if self.scr_num == 0 and irm_nflag == 0:
                sec_flag = 1
                mute = getMuteStatus(MA_CTRL)
                if mute == 0:
                    update_M = 1
                    setMuteStatus(MA_CTRL)
                    setMuteStatus(DIG_CTRL)
                else:
                    update_M = 0
                    setMuteStatus(MA_CTRL)
                    setMuteStatus(DIG_CTRL)
            elif self.scr_num == 1:
                if m_indx == 1:
                    self.bootScr()
                elif m_indx == 2:
                    self.hvScr4()
                elif m_indx == 3:
                    self.filtScr()
                elif m_indx == 4:
                    self.spScr5()
            elif self.scr_num == 2:
                self.menuScr()
            elif self.scr_num == 3:
                if f_indx == 1:
                    self.phScr9()
                elif f_indx == 2:
                    self.hpScr6()
                elif f_indx == 3:
                    self.deScr7()
                elif f_indx == 4:
                    self.nonScr8()
            elif self.scr_num == 4:
                ok_flag = 0
                mute = getMuteStatus(HV_CTRL)
                if mute != hv_en:
                    update_M = hv_en
                    setMuteStatus(HV_CTRL)
                self.menuScr()
            elif self.scr_num == 5:
                ok_flag = 0
                filter_cur = getFilterStatus()
                if filter_cur != fil_sp:
                    filter_mod = fil_sp
                    setFilterStatus()
                self.menuScr()
            elif self.scr_num == 6:
                ok_flag = 0
                mute = getMuteStatus(HP_CTRL)
                if mute != hp_fil:
                    update_M = hp_fil
                    setMuteStatus(HP_CTRL)
                self.filtScr()
            elif self.scr_num == 7:
                ok_flag = 0
                mute = getMuteStatus(DE_CTRL)
                if mute != de_emp:
                    update_M = de_emp
                    setMuteStatus(DE_CTRL)
                self.filtScr()
            elif self.scr_num == 8:
                ok_flag = 0
                mute = getMuteStatus(NON_CTRL)
                if mute != non_os:
                    update_M = non_os
                    setMuteStatus(NON_CTRL)
                self.filtScr()
            elif self.scr_num == 9:
                ok_flag = 0
                mute = getMuteStatus(PH_CTRL)
                if mute != ph_comp:
                    update_M = ph_comp
                    setMuteStatus(PH_CTRL)
                self.filtScr()

        if bs3 == 1 or ir3 == 1:
            time.sleep(0.1)
            bs3 = 0
            ir3 = 0
            if self.scr_num == 0:
                getVol()
                alsa_hvol = alsa_cvol
                if alsa_hvol < 255 and alsa_hvol >= 240:
                    alsa_hvol += 1
                if alsa_hvol < 240 and alsa_hvol >= 210:
                    alsa_hvol += 3
                if alsa_hvol < 210 and alsa_hvol >= 120:
                    alsa_hvol += 10
                if alsa_hvol < 120 and alsa_hvol >= 0:
                    alsa_hvol += 30
                setVol()
                self.screenVol()
            elif self.scr_num == 1:
                if m_indx > 1:
                    m_indx -= 1
                self.menuScr()
            elif self.scr_num == 3:
                if f_indx > 1:
                    f_indx -= 1
                self.filtScr()

        if bs4 == 1 or ir4 == 1:
            time.sleep(0.1)
            bs4 = 0
            ir4 = 0
            if self.scr_num == 0:
                getVol()
                alsa_hvol = alsa_cvol
                if alsa_hvol <= 255 and alsa_hvol > 240:
                    alsa_hvol -= 1
                if alsa_hvol <= 240 and alsa_hvol > 210:
                    alsa_hvol -= 3
                if alsa_hvol <= 210 and alsa_hvol > 120:
                    alsa_hvol -= 10
                if alsa_hvol <= 120 and alsa_hvol > 0:
                    alsa_hvol -= 30
                setVol()
                self.screenVol()
            elif self.scr_num == 1:
                m_indx += 1
                if m_indx > 4:
                    m_indx = 1
                self.menuScr()
            elif self.scr_num == 3:
                f_indx += 1
                if f_indx > 4:
                    f_indx = 1
                self.filtScr()
            elif self.scr_num == 4:
                if ok_flag == 0:
                    ok_flag = 1
                self.hvScr4()
            elif self.scr_num == 5:
                if ok_flag == 0:
                    ok_flag = 1
                self.self.spScr5()
            elif self.scr_num == 6:
                if ok_flag == 0:
                    ok_flag = 1
                self.self.hpScr6()
            elif self.scr_num == 7:
                if ok_flag == 0:
                    ok_flag = 1
                self.self.deScr7()
            elif self.scr_num == 8:
                if ok_flag == 0:
                    ok_flag = 1
                self.self.nonScr8()
            elif self.scr_num == 9:
                if ok_flag == 0:
                    ok_flag = 1
                self.self.phScr9()

        if bs5 == 1 or ir5 == 1:
            time.sleep(0.1)
            bs5 = 0
            ir5 = 0
            if self.scr_num == 0:
                self.lcd.clearScreen()
                self.menuScr()
            elif self.scr_num == 1:
                self.screenVol()
            elif self.scr_num == 2:
                self.menuScr()
            elif self.scr_num == 3:
                self.menuScr()
            elif self.scr_num == 4:
                if hv_en == 1:
                    hv_en = 0
                self.hvScr4()
            elif self.scr_num == 5:
                if fil_sp == 1:
                    fil_sp = 0
                self.spScr5()
            elif self.scr_num == 6:
                if hp_fil == 1:
                    hp_fil = 0
                self.hpScr6()
            elif self.scr_num == 7:
                if de_emp == 1:
                    de_emp = 0
                self.deScr7()
            elif self.scr_num == 8:
                if non_os == 1:
                    non_os = 0
                self.nonScr8()
            elif self.scr_num == 9:
                if ph_comp == 1:
                    ph_comp = 0
                self.phScr9()

        if sec_flag == 1:
            if self.scr_num == 0:
                self.screenVol()
                sec_flag = 0
        led_off_counter += 1

    def bootScr(self):
        global scr_num
        if self.scr_num != 2:
            self.scr_num = 2
            lcd.clearScreen()
        lcd.clearScreen()
        h_ip = get_ip_address("eth0")
        w_ip = get_ip_address("wlan0")
        lcd.displayString(A_CARD1, 0, 0)
        lcd.displayStringNumber(h_ip, 2, 0)
        lcd.displayString(h_name, 4, 0)
        lcd.displayStringNumber(w_ip, 6, 0)

    def infoScr(self):
        global scr_num
        if self.scr_num != 0:
            self.scr_num = 0
            lcd.clearScreen()

        lcd.displayString("VOL", 1, 0)
        lcd.displayString("0.0dB", 1, 60)
        lcd.displayString("PCM/DSD", 3, 0)
        lcd.displayString("SR", 5, 0)
        lcd.displayString("44.1kHz", 5, 60)

    def hvScr4(self):
        global hv_en
        global ok_flag
        if self.scr_num != 4:
            self.scr_num = 4
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

    def menuScr(self):
        global m_indx
        if self.scr_num != 1:
            self.scr_num = 1
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

    def filtScr(self):
        global fil_sp
        global hp_fil
        global de_emp
        global non_os
        global ph_comp
        global f_indx
        if self.scr_num != 3:
            self.scr_num = 3
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

    def spScr5(self):
        global fil_sp
        global ok_flag
        if self.scr_num != 5:
            self.scr_num = 5
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
        if self.scr_num != 6:
            self.scr_num = 6
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
        if self.scr_num != 7:
            self.scr_num = 7
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
        if self.scr_num != 8:
            self.scr_num = 8
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
        if self.scr_num != 9:
            self.scr_num = 9
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
        global mute
        if self.scr_num != 0:
            self.scr_num = 0
            lcd.clearScreen()
        if self.scr_num == 0:
            left_db, _ = getVol()
            alsa_vol = "{:.2f}dB".format(left_db)
            if left_db == 0.0:
                lcd.displayString("    ", 1, 80)
            elif left_db > -10.0:
                lcd.displayString("    ", 1, 90)
            elif left_db > -100.0:
                lcd.displayString("  ", 1, 100)
            lcd.displayString(alsa_vol, 1, 20)
            mute = getMuteStatus(MA_CTRL)
            if mute == 0:
                lcd.displayString("@", 3, 50)
            else:
                lcd.displayString("  ", 3, 50)
            getHwparam()


def shell_cmd(cmd, timeout=SUBPROCESS_TIMEOUT):
    """Run a shell command and return the stdout."""
    out = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    stdout, stderr = out.communicate(timeout=timeout)
    return stdout, stderr


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
        print("No Boss2")
        return None
    else:
        return card_number


def getMuteStatus(mixerCtrl):
    global card_num
    cmd = ["amixer", "-c", str(card_num), "get", "'{}'".format(mixerCtrl)]
    out, _ = shell_cmd(cmd)
    if "off" in out:
        return 0
    else:
        return 1


def setMuteStatus(mixerCtrl):
    global card_num
    global update_M
    if update_M == 0:
        shell_cmd(["amixer", "-c", card_num, "set", mixerCtrl, "mute"])
    else:
        shell_cmd(["amixer", "-c", card_num, "set", mixerCtrl, "unmute"])


def getFilterStatus():
    global card_num

    out, _ = shell_cmd(["amixer", "-c", card_num, "get", "'PCM Filter Speed'"])
    lines = [line for line in out.split("\n") if "Item0" in line]
    if not lines:
        return 1
    word_str = lines[0].split()
    current_status = word_str[1]
    if current_status == "'Slow'":
        return 0
    else:
        return 1


def setFilterStatus():
    global card_num
    global filter_mod
    if filter_mod == 0:
        val = "Slow"
    else:
        val = "Fast"

    cmd = ["amixer", "-c", card_num, "set", "'PCM Filter Speed'", val]
    shell_cmd(cmd)


def getVol():
    global alsa_cvol
    global card_num
    CARD_NUMBER = card_num
    MIXER_CONTROL = "Master"
    left_db_str = "[-127.50dB]"
    left_hrdware_val = 0
    right_db_str = "[-127.50dB]"
    stdout, stderr = shell_cmd(["amixer", "-c", CARD_NUMBER, "get", MIXER_CONTROL])
    if not stderr:
        line_str = stdout.split("\n")
        for line in line_str:
            if "Front Left:" in line:
                word_str = line.split()
                left_hrdware_val = word_str[3]
                left_db_str = word_str[5]
                left_db_str = left_db_str.replace("[", "")
                left_db_str = left_db_str.replace("]", "")
            if "Front Right:" in line:
                word_str = line.split()
                right_db_str = word_str[5]
                right_db_str = right_db_str.replace("[", "")
                right_db_str = right_db_str.replace("]", "")
    else:
        print("Error getting volume: {}".format(stderr))

    left_db_float = float(left_db_str.split("dB")[0])
    right_db_float = float(right_db_str.split("dB")[0])

    alsa_cvol = int(left_hrdware_val)

    return (left_db_float, right_db_float)


def setVol():
    global alsa_hvol
    global alsa_cvol
    global card_num
    CARD_NUMBER = card_num
    MIXER_CONTROL = "Master"
    MIXER_CONTROL1 = "Digital"

    getVol()
    setflag = 0
    if alsa_cvol == alsa_hvol:
        setflag = 1
    elif alsa_hvol < 0 or alsa_hvol > 255:
        setflag = 1
    else:
        cmd = (
            "amixer",
            "-c",
            CARD_NUMBER,
            "set",
            MIXER_CONTROL,
            "{left},{right}".format(left=alsa_hvol, right=alsa_hvol),
        )
        cmd1 = (
            "amixer",
            "-c",
            CARD_NUMBER,
            "set",
            MIXER_CONTROL1,
            "{left},{right}".format(left=alsa_hvol, right=alsa_hvol),
        )
        shell_cmd(cmd)
        shell_cmd(cmd1)

    return setflag


def getHwparam():
    global card_num
    global bit_rate
    global bit_format
    global last_bit_format
    global led_off_counter
    CARD_NUMBER = card_num
    hw_format = ""
    hw_rate_num = ""
    if CARD_NUMBER == -1:
        hw_param_out = "No " + A_CARD1
    else:
        hw_cmd = "/proc/asound/card" + str(CARD_NUMBER) + "/pcm0p/sub0/hw_params"
        stdout, _ = shell_cmd(["cat", hw_cmd])
        hw_param_str = stdout.rstrip().splitlines()
        if hw_param_str[0] == "closed":
            hw_param_out = "closed"
        else:
            for line in hw_param_str:
                if line.startswith("format:"):
                    format_val = line.split(":")
                    hw_format = format_val[1].strip()
                if str(line).find("rate:") != -1:
                    rate_val = line.split(":")
                    hw_rate = rate_val[1].strip()
                    hw_rate_line = hw_rate.split()
                    hw_rate_num = int(hw_rate_line[0])
            hw_param_out = [hw_format, hw_rate_num]
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
        led_off_counter = 0
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
        led_off_counter = 0
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
        led_off_counter = 0
    else:
        bit_rate = "closed"
        lcd.displayStringNumber("   ", 5, 15)
        lcd.displayString(" ", 5, 5)
        lcd.displayString("        ", 5, 50)
        last_bit_format = 0
    return hw_param_out


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
        print("Unable to obtain IP address for {} -- {}".format(ifname, err))
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


def main():
    global h_name
    global card_num
    global led_off_counter
    global lcd
    led_off_counter = 1
    i2cConfig()
    lcd = SH1106LCD()
    h_ip = get_ip_address("eth0")
    w_ip = get_ip_address("wlan0")
    h_name = "HOST:%s" % socket.gethostname()
    lcd.displayStringNumber(h_ip, 0, 0)
    lcd.displayStringNumber(w_ip, 6, 0)
    lcd.displayString(h_name, 2, 0)
    lcd.displayString(A_CARD1, 4, 0)
    time.sleep(SPLASH_SCREEN_TIMEOUT)

    lcd.clearScreen()
    card_num = getCardNumber()
    if card_num is None:
        print("no card detected")
        lcd.displayString("NO BOSS2", 4, 5)
        lcd.displayStringNumber(h_ip, 0, 0)
        lcd.displayStringNumber(w_ip, 6, 0)
        exit(0)

    time.sleep(0.04)
    init_gpio_bcm()
    ir = IRModule.IRRemote(callback="DECODE")
    GPIO.add_event_detect(IR_PIN, GPIO.BOTH, callback=ir.pWidth)
    ir.set_callback(remote_callback)
    gui = GUI(lcd)
    try:
        gui.screenVol()
        update_status()
        while True:
            gui.do_update()
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        print("Cleaning up...")
        if lcd:
            try:
                lcd.display_off()
                lcd.clearScreen()
            except Exception as err:
                print("Unable to clear LCD: {}".format(err))
        ir.remove_callback()
        GPIO.cleanup(IR_PIN)
        GPIO.cleanup(SW1)
        GPIO.cleanup(SW2)
        GPIO.cleanup(SW3)
        GPIO.cleanup(SW4)
        GPIO.cleanup(SW5)


if __name__ == "__main__":
    main()
