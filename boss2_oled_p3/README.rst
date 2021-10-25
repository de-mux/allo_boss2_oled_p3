.. sidebar::

    .. contents::

The BOSS2 OLED application runs on Python 3.4 and higher.

It handles the front panel display and user interface, including:

- volume settings
- controlling Allo Boss2 amixer controls
- filter settings
- RMS voltage level

Tested on:

- RoPieee
- RoPieee XL
- MoOde
- DietPi
- Volumio
- Max2play
- OSMC

Installation - OSMC
===================

- Login as root user

.. code:: bash

    cd /tmp
    git clone https://github.com/de-mux/allo_boss2_oled_p3.git
    cd boss2_oled_p3
    ./install_boss2_oled.sh

After installation, the splash screen should appear on the front panel display
for a brief moment, and should then display the main screen with volume setting
and bitstream info if audio is playing.

To uninstall
------------

.. code:: bash

    sudo /opt/boss2_oled/uninstall.sh


Installation - RoPieee, RoPieee XL, MoOde, DietPi, Volumio, Max2play
====================================================================

- Login as root user

.. code:: bash

    cd /opt/
    git clone https://github.com/de-mux/allo_boss2_oled_p3.git
    cd boss2_oled_p3
    ./install_boss2_oled.sh

Automatically downloads and installs required packages for the respective OS and reboots.
Every reboot starts boss2_oled display, checks the Boss2 sound device on startup.
If no Boss2 hardware is found the application exits.


Other OS
========

If Python 2 is not installed, install manually.

Required packages after installing python2::

  apt-get -y update
  apt-get install python3
  apt-get -y install python3-rpi.gpio (if doesnt work install pip and then run pip2 install RPi.GPIO==0.7.0)
  apt-get -y install python3-pip
  apt-get -y install python3-smbus (if does not work then run pip2 install smbus)
  apt-get -y install python3-pil  (or apt-get -y install python3-pillow)

Enable i2c manually or check ``i2cdetect -y 1``.

piCorePlayer v7.0.0 onwards
---------------------------
Resize FS on webGUI
ssh login with user tc Password piCore

.. code:: bash

    tce-load -wi python3.8-Pillow.tcz
    tce-load -wi python3.8-smbus.tcz
    tce-load -wi python3.8-rpi-gpio.tcz
    tce-load -wi iproute2.tcz

    sudo su
    cd /opt/
    wget https://raw.githubusercontent.com/allocom/allo_boss2_oled_p3/main/boss2_oled_p3.tar.gz
    tar -xzvf boss2_oled_p3.tar.gz

On web GUI Tweaks page user commands type below line and save::

    sh /opt/boss2_oled_p3/oled_run.sh


Disabling the startup service
=============================

On executing ./install_boss2_oled.sh  will install the required packages and
add the startup service to start on every reboot. If for any reason you need to
manually disable it on startup, follow the steps below.

RoPieee
-------

- ssh enable on GUI
- Login via SSH (username: ``root``, password: ``ropieee``)

for disabling the boss2 oled application execute below command on ssh login
$systemctl disable ropieee-boss2-oled.service
$reboot

To start agin the service execute below command and reboot.
$systemctl enable ropieee-boss2-oled.service
$reboot

OSMC
----

- Login via SSH (username: ``osmc``, password: ``osmc``)

To disable the service::

  systemctl stop boss2oled.service
  systemctl disable boss2oled.service

To re-enable the service::

  systemctl enable boss2oled.service
  systemctl start boss2oled.service

DietPi
------

- Login via SSH (username: ``root``, password: ``dietpi``)

To disable the service::

  systemctl disable boss2oled.service
  reboot

To re-enable the service::

  systemctl enable boss2oled.service
  reboot

MoOde
-----

- Login via SSH (username: ``pi``, password: ``moodeaudio``)
- ``sudo su``

For disabling start up service, follow the steps below:

- ``nano /etc/rc.local``
- delete or comment these 2 lines::

    boss2flag=1
    sudo python3 /opt/boss2_oled_p3/boss2_oled.py &

Volumio
-------

- Login via SSH (username: ``volumio``, password: ``volumio``)
- ``su`` (password: volumio)

For disabling start up service, follow the steps below:

- ``nano /etc/rc.local``
- delete or comment these 2 lines::

    boss2flag=1
    sudo python3 /opt/boss2_oled_p3/boss2_oled.py &

Max2Play
--------

- Login via SSH (username: ``pi``, password: ``max2play``)
- ``sudo su``

For disabling start up service, follow the steps below:

- ``nano /etc/rc.local``
- delete or comment these 2 lines::

    boss2flag=1
    sudo python3 /opt/boss2_oled_p3/boss2_oled.py &
