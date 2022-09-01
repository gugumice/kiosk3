#!/bin/bash

sudo raspi-config nonint do_memory_16
systemctl disable bluetooth.service
systemctl disable hciuart.service

ln /opt/kiosk/kiosk.service /lib/systemd/system/kiosk.service
ln /opt/kiosk/firstboot.service /lib/systemd/system/firstboot.service
ln /opt/kiosk/kiosk.ini /home/pi/kiosk.ini
systemctl enable firstboot.service


sed '/^# Additional overlays.*/a dtoverlay=pi3-disable-wifi\ndtoverlay=pi3-disable-bt' /boot/config.txt
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install cups cups-bsd libcups2-dev
cupsctl --remote-admin --remote-any
usermod -a -G lpadmin pi
addgroup watchdog
usermod -a -G watchdog pi
service cups restart
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install python3-pip
echo 'KERNEL=="watchdog", MODE="0660", GROUP="watchdog"' > /etc/udev/rules.d/60-watchdog.rules
sed '/^#NTP=.*/a FallbackNTP=laiks.egl.local' /etc/systemd/timesyncd.conf
chattr -i /etc/hosts
echo '10.100.20.104   laiks.egl.local' > /etc/hosts
chattr +i /etc/hosts
pip3 --no-input install pycups pycurl pyserial configparser
