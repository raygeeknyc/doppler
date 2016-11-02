#!/bin/bash
logger "$0"
logger "$0 waiting and rebooting renderer nodes"
sleep 5
./rebootnodes.sh
logger "$0 waiting 60s for reboots"
sleep 60
<<<<<<< HEAD
logger "killing startsensor.sh"
sudo killall -9 startsensor.sh
./startupnodes.sh
=======
./startupnodes.sh < /dev/null
>>>>>>> ef7f26851762e3ae41f544a6d425b06fb20b2fdc
logger "$0 waiting 30s for node startup"
sleep 30
./set_modules.sh
./startsensor.sh < /dev/null
