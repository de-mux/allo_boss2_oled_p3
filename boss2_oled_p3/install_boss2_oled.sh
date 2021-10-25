#!/bin/bash
HOSTNAME="$(uname -n)"
BASE_DIR="${BASH_SOURCE%/*}"
SERVICE_DIR=/etc/systemd/system/
INSTALL_DIR="/opt/boss2_oled"
VENV="venv"
VENV_PATH="${INSTALL_DIR}/${VENV}"

function check_py {
    HAS_PY34="false"
    ver_str=$(sudo python3 -c 'import sys; version = sys.version_info[:3]; print("{0}.{1}.{2}".format(*version))' 2>&1)
    IFS='.' read -r -a PY_VER <<<"$ver_str"
    if [ ${PY_VER[0]} -eq 3 ]; then
        if [ ${PY_VER[1]} -ge 4 ]; then
            HAS_PY34="true"
        fi
    elif [ ${PY_VER[0]} -gt 3 ]; then
        HAS_PY34="true"
    fi

    if [ $HAS_PY34 != "true" ]; then
        echo "PYTHON version mismatch"
        echo "PYTHON version 3.4 or above required"
        echo "Installed version: ${ver_str}"
        exit 1
    fi
}

function install_py_environment {
    echo
    echo Creating Python virtual environment in ${VENV_PATH}...
    sudo python3 -m venv ${VENV_PATH}

    echo Installing Python requirements to ${VENV_PATH}...
    PYTHON_BIN=${VENV_PATH}/bin/python
    sudo $PYTHON_BIN -m pip install -U pip
    sudo $PYTHON_BIN -m pip install -r ${BASE_DIR}/requirements.txt
    echo Finished creating virtual environment: ${VENV_PATH}
}

function install_py_files {
    sudo cp -v -r ${BASE_DIR} ${INSTALL_DIR}
}

check_py


if [ $HOSTNAME == "ropieeexl" ]; then
	ropieeeflag=2
elif [ $HOSTNAME == "ropieee" ]; then
	ropieeeflag=1
else
	ropieeeflag=0
fi

set -e

if [ $HOSTNAME == "moode" ]; then
	echo "******************************************"
	echo "******************************************"
	echo "****                                  ****"
	echo "****              MOODE               ****"
	echo "****                                  ****"
	echo "******************************************"
	echo "******************************************"
	sudo apt-get -y update
	sudo apt-get -y install python3-pip
	sudo apt-get -y install python3-smbus
	sudo apt-get -y install python3-pil
	#sudo apt-get -y install python-netifaces
	sudo raspi-config nonint do_i2c 0
	while read line; do
		if [ "$line" == "boss2flag=1" ]; then
			flag=1
		fi
	done <$RC_LOCAL
	if [ "$flag" == "1" ]; then
		echo "already installed"
		exit 0
	else
		sudo sed -i "$(wc -l </etc/rc.local)i\\boss2flag=1\\" /etc/rc.local
		sudo sed -i "$(wc -l </etc/rc.local)i\\sudo python3 /opt/boss2_oled_p3/boss2_oled.py &\\" /etc/rc.local
		echo "******************************************"
		echo "***      Successfully Installed        ***"
		echo "******************************************"
		sleep 5
		sudo reboot
	fi
fi
if [ $HOSTNAME == "volumio" ]; then
	echo "******************************************"
	echo "******************************************"
	echo "****                                  ****"
	echo "****             VOLUMIO              ****"
	echo "****                                  ****"
	echo "******************************************"
	echo "******************************************"
	sudo apt-get -y update
	sudo apt-get -y install python3-pip
	sudo apt-get -y install python3-smbus
	sudo apt-get -y install python3-pil
	sudo apt-get -y install python3-dev
	#sudo apt-get -y install python-netifaces
	sudo pip install RPi.GPIO==0.7.0
	while read line; do
		if [ "$line" == "boss2flag=1" ]; then
			flag=1
		fi
	done <$RC_LOCAL
	if [ "$flag" == "1" ]; then
		echo "already installed"
		exit 0
	else
		sudo sed -i "$(wc -l </etc/rc.local)i\\boss2flag=1\\" /etc/rc.local
		sudo sed -i "$(wc -l </etc/rc.local)i\\sudo python3 /opt/boss2_oled_p3/boss2_oled.py &\\" /etc/rc.local
		echo "******************************************"
		echo "***      Successfully Installed        ***"
		echo "******************************************"
		sleep 5
		reboot
	fi

fi

if [ $HOSTNAME == "DietPi" ]; then
	echo "******************************************"
	echo "******************************************"
	echo "****                                  ****"
	echo "****             DIETPI               ****"
	echo "****                                  ****"
	echo "******************************************"
	echo "******************************************"
	sudo apt-get -y update
	sudo apt-get -y install python3-rpi.gpio
	sudo apt-get -y install python3-pip
	sudo apt-get -y install python3-smbus
	sudo apt-get -y install python3-pil
	udo apt-get -y install raspi-config
	sudo apt-get -y install i2c-tools
	sleep 2
	sudo raspi-config nonint do_i2c 0
	#sudo apt-get -y install python-netifaces
	sudo cp /opt/boss2_oled_p3/boss2oled.service ${SERVICE_DIR}
	sudo systemctl enable boss2oled.service
	#sudo /boot/dietpi/dietpi-software install 72
	echo "******************************************"
	echo "***      Successfully Installed        ***"
	echo "******************************************"
	sleep 5
	reboot

fi


if [ $HOSTNAME == "osmc" ] || [ -z $(id -u osmc &>/dev/null) ]; then
	echo "******************************************"
	echo "******************************************"
	echo "****                                  ****"
	echo "****              OSMC                ****"
	echo "****                                  ****"
	echo "******************************************"
	echo "******************************************"

	sudo apt-get -y update
	sudo apt-get -y install libjpeg-dev zlib1g-dev
	sudo apt-get -y install alsa-utils
	sudo apt-get -y install python3-venv

    install_py_environment
    install_py_files

    # Install and enable service
    SERVICE=osmc-boss2oled.service
    sudo systemctl stop ${SERVICE} 2>&1 /dev/null
	sudo cp ${BASE_DIR}/${SERVICE} ${SERVICE_DIR}
    EXEC_START="${VENV_PATH}/bin/python ${INSTALL_DIR}/boss2_oled.py"
    sudo sed -i "s#ExecStart=.\\+#ExecStart=${EXEC_START} --logfile /tmp/boss2.log#" ${SERVICE_DIR}/${SERVICE}
	sudo systemctl enable ${SERVICE}
	sudo systemctl start ${SERVICE}

    # Copy uninstall script
    sudo tee ${INSTALL_DIR}/uninstall.sh <<- EOF
#!/bin/bash
sudo systemctl stop ${SERVICE} 2>&1 /dev/null
sudo systemctl disable ${SERVICE} 2>&1 /dev/null
sudo rm -r ${SERVICE_DIR}/${SERVICE} 2>&1 /dev/null
sudo rm -r ${INSTALL_DIR} 2>&1 /dev/null
EOF
    sudo chmod +x ${INSTALL_DIR}/uninstall.sh

	echo "******************************************"
	echo "***      Successfully Installed        ***"
	echo "******************************************"
fi


if [ $HOSTNAME == "max2play" ]; then
	echo "******************************************"
	echo "******************************************"
	echo "****                                  ****"
	echo "****              MAX2PLAY            ****"
	echo "****                                  ****"
	echo "******************************************"
	echo "******************************************"
	sudo apt-get -y update
	sudo apt-get -y install python3-rpi.gpio
	sudo apt-get -y install python3-pip
	sudo apt-get -y install python3-smbus
	sudo apt-get -y install python3-pil
	#sudo apt-get -y install python-netifaces
	sudo raspi-config nonint do_i2c 0
	while read line; do
		if [ "$line" == "boss2flag=1" ]; then
			flag=1
		fi
	done <$RC_LOCAL
	if [ "$flag" == "1" ]; then
		echo "already installed"
		exit 0
	else
		sudo sed -i "$(wc -l </etc/rc.local)i\\boss2flag=1\\" /etc/rc.local
		sudo sed -i "$(wc -l </etc/rc.local)i\\sudo python3 /opt/boss2_oled_p3/boss2_oled.py &\\" /etc/rc.local
		echo "******************************************"
		echo "***      Successfully Installed        ***"
		echo "******************************************"
		sleep 5
		sudo reboot
	fi

fi

if [ $ropieeeflag == "1" ] || [ $ropieeeflag == "2" ]; then
	echo "******************************************"
	echo "******************************************"
	echo "****                                  ****"
	echo "****             ROPIEEE              ****"
	echo "****                                  ****"
	echo "******************************************"
	echo "******************************************"
	yes | pacman -S python3-pip gcc
	pip3 install RPi.GPIO
	pip3 install smbus
	yes | pacman -S python3-pillow
	yes | pacman -S inetutils
	while read line; do
		if [ "$line" == "i2c-dev" ]; then
			flag=1
		fi
	done </etc/modules-load.d/raspberrypi.conf
	if [ "$flag" == "1" ]; then
		echo "already added"
		exit 0
	else
		echo "i2c-dev" >>/etc/modules-load.d/raspberrypi.conf
	fi
	cp /opt/boss2_oled_p3/ropieee-boss2-oled.service ${SERVICE_DIR}
	systemctl enable ropieee-boss2-oled.service
	echo "******************************************"
	echo "***      Successfully Installed        ***"
	echo "******************************************"
	sleep 5
	reboot
fi
