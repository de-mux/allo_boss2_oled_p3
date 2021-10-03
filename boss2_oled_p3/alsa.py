from types import SimpleNamespace

from utils import shell_cmd


class AlsaMixer:
    def __init__(self, card_num, card_name):
        self.card_num = card_num
        self.card_name = card_name

    def getMuteStatus(self, mixerCtrl):
        cmd = ["amixer", "-c", str(self.card_num), "get", "'{}'".format(mixerCtrl)]
        out, _ = shell_cmd(cmd)
        if "off" in out:
            return 0
        else:
            return 1

    def setMuteStatus(self, mixerCtrl, update_M):
        if update_M == 0:
            shell_cmd(["amixer", "-c", self.card_num, "set", mixerCtrl, "mute"])
        else:
            shell_cmd(["amixer", "-c", self.card_num, "set", mixerCtrl, "unmute"])

    def getVol(self):
        MIXER_CONTROL = self.CONTROL.MA_CTRL
        left_db_str = "[-127.50dB]"
        right_db_str = "[-127.50dB]"
        left_hrdware_val = 0
        stdout, stderr = shell_cmd(
            ["amixer", "-c", self.card_num, "get", MIXER_CONTROL]
        )
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

        return alsa_cvol, left_db_float, right_db_float

    def setVol(self, alsa_hvol):
        CARD_NUMBER = self.card_num
        MIXER_CONTROL = "Master"
        MIXER_CONTROL1 = "Digital"

        alsa_cvol, _, _ = self.getVol()
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

    def getHwparam(self):
        hw_format = ""
        hw_rate_num = ""
        if self.card_num == -1:
            hw_format = "No " + self.card_name
        else:
            hw_cmd = "/proc/asound/card" + str(self.card_num) + "/pcm0p/sub0/hw_params"
            stdout, _ = shell_cmd(["cat", hw_cmd])
            hw_param_str = stdout.rstrip().splitlines()
            if hw_param_str[0] == "closed":
                hw_format = "closed"
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
        return hw_format, hw_rate_num


class AlsaMixerBoss2(AlsaMixer):
    CONTROL = SimpleNamespace(
        DE_CTRL="PCM De-emphasis Filter",
        HP_CTRL="PCM High-pass Filter",
        PH_CTRL="PCM Phase Compensation",
        NON_CTRL="PCM Nonoversample Emulate",
        HV_CTRL="HV_Enable",
        SP_CTRL="PCM Filter Speed",
        MA_CTRL="Master",
        DIG_CTRL="Digital",
    )

    def getFilterStatus(self):
        out, _ = shell_cmd(["amixer", "-c", self.card_num, "get", "'PCM Filter Speed'"])
        lines = [line for line in out.split("\n") if "Item0" in line]
        if not lines:
            return 1
        word_str = lines[0].split()
        current_status = word_str[1]
        if current_status == "'Slow'":
            return 0
        else:
            return 1

    def setFilterStatus(self, filter_mod):
        if filter_mod == 0:
            val = "Slow"
        else:
            val = "Fast"

        cmd = ["amixer", "-c", self.card_num, "set", "'PCM Filter Speed'", val]
        shell_cmd(cmd)

    def update_status(self):
        self.getMuteStatus(self.CONTROL.MA_CTRL)
        hp_fil = self.getMuteStatus(self.CONTROL.HP_CTRL)
        hv_en = self.getMuteStatus(self.CONTROL.HV_CTRL)
        non_os = self.getMuteStatus(self.CONTROL.NON_CTRL)
        ph_comp = self.getMuteStatus(self.CONTROL.PH_CTRL)
        de_emp = self.getMuteStatus(self.CONTROL.DE_CTRL)
        fil_sp = self.getFilterStatus()

        return hp_fil, hv_en, non_os, ph_comp, de_emp, fil_sp
