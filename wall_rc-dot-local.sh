#!/bin/sh -e
#
# rc.local
#
# This script is executed at the end of each multiuser runlevel.
# Make sure that the script will "exit 0" on success or any other
# value on error.
#
# In order to enable or disable this script just change the execution
# bits.
#
# By default this script does nothing.
logger "starting doppler wall from rc.local"
su --login --command "cd /home/doppler/doppler;nohup ./start_wall.sh &" doppler
exit 0
