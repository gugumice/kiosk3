#!/bin/bash
if [ ! -e /home/pi ]; then
    echo "Only run this on your pi."
    exit 1
fi
systemctl enable kiosk.service
systemctl disable firstboot.service
raspi-config --expand-rootfs > /dev/null
sleep 5
IPO=$(ip -o -4 addr list eth0 | awk '{print $4}' | cut -d/ -f1 |  cut -d. -f2);
NEW_HOSTNAME="rpi-kio-"$IPO
raspi-config nonint do_hostname $NEW_HOSTNAME
