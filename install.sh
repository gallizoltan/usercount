#!/bin/bash

sudo apt update

sudo apt install -y python3-pip gnuplot-qt

# tipp: sudo mv /usr/lib/python3.12/EXTERNALLY-MANAGED /usr/lib/python3.12/EXTERNALLY-MANAGED.old

pip3 install Mastodon.py
pip3 install psutil
