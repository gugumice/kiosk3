#!/bin/bash
if [ ! -e /home/pi ]; then
    echo "Only run this on your pi."
    exit 1
fi
systemctl enable kiosk.service
systemctl disable firstboot.service
raspi-config --expand-rootfs > /dev/null
CURRENT_HOSTNAME=$(cat /proc/sys/kernel/hostname)
sleep 5
#set kostname to name+second ocet of ip address
NEW_HOSTNAME="rpi-kio3-"$(ip -o -4 addr list eth0 | awk '{print $4}' | cut -d/ -f1 |  cut -d. -f2);
chattr -i /etc/hostname
echo "$NEW_HOSTNAME" > "/etc/hostname"
chattr -i /etc/hosts
sed -i "s/127.0.1.1.*$CURRENT_HOSTNAME/127.0.1.1\t$NEW_HOSTNAME/g" /etc/hosts
hostname $NEW_HOSTNAME
chattr +i /etc/hostname
chattr +i /etc/hosts
/usr/sbin/shutdown -r now
