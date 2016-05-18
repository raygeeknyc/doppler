#!/bin/bash
logger "$0"
logger "killing startsensor.sh"
sudo killall -9 startsensor.sh
./rebootnodes.sh
logger "$0 waiting 60s for reboots"
sleep 60
./startupnodes.sh
logger "$0 waiting 30s for node startup"
sleep 30
./startsensor.sh
