#!/bin/bash

if [[ $EUID -ne 0 ]]; then
  echo "You must be root" 2>&1
  exit 1
fi

apt update
apt install -y tor
apt install -y python3-pip
apt install -y gnuplot-qt
usermod -a -G debian-tor $(whoami)
service tor restart

pip3 install Mastodon.py
pip3 install pysocks
pip3 install psutil
