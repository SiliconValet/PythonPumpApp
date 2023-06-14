#!/bin/sh

cd /home/jassmith/app
. ./env/bin/activate
python3 main.py >/dev/null 2>&1
