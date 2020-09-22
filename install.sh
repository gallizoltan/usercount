#!/bin/bash

if [[ $EUID -ne 0 ]]; then
  echo "You must be root" 2>&1
  exit 1
fi

apt update 
apt install tor
apt install python3-pip
apt install gnuplot5-qt
usermod -a -G debian-tor $(whoami)
service tor restart
