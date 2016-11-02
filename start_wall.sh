#!/bin/bash
logger "$0"
logger "$0 waiting and rebooting renderer nodes"
sleep 5
./rebootnodes.sh
logger "$0 waiting 60s for reboots"
sleep 60
logger "killing startsensor.sh"
sudo killall -9 startsensor.sh
./startupnodes.sh
logger "$0 waiting 30s for node startup"
sleep 30
./startsensor.sh < /dev/null
