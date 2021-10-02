import os
import sys

if os.name != "posix":
    sys.exit("platform not supported")
import socket
import fcntl
import struct
from Hardware.SH1106.SH1106LCD import *
from Hardware.SH1106.SH1106FontLib import *
from Hardware.I2CConfig import *


h_ip = ""


def network1(ifname):
    ip_address = ""
    global w_ip
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        ip_address = socket.inet_ntoa(
            fcntl.ioctl(s.fileno(), 0x8915, struct.pack("256s", ifname[:15]))[20:24]
        )
    except Exception:
        ip_address = ""
    if ifname == "eth0":
        print("eth0 is ", ip_address)
        try:
            ipv4 = os.popen("ip addr show eth0").read().split("inet ")[1].split("/")[0]
            print("IP Address", ipv4)
        except Exception:
            ipv4 = ""
        return ipv4
    else:
        try:
            w_ip = os.popen("ip addr show wlan0").read().split("inet ")[1].split("/")[0]
        except Exception:
            w_ip = ""
        print("wlan0 is ", w_ip)
    return ip_address


def main():
    global h_ip
    global w_ip
    h_ip = network1("eth0")
    w_ip = network1("wlan0")
    print("eth0 is", h_ip)


if __name__ == "__main__":
    main()
