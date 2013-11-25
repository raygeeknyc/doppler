#!/usr/bin/env python
import freenect
import time
import sys
 
TILT_MAX = 20
TILT_STEP = 02
TILT_START = -35 
 
if len(sys.argv) >= 2:
	if sys.argv[1]: TILT_MAX = int(sys.argv[1])
	if sys.argv[2]: TILT_STEP = int(sys.argv[2])
	if sys.argv[2]: TILT_START = int(sys.argv[3])
 
ctx = freenect.init()
print "Number of kinects: %d\n" % freenect.num_devices(ctx)
dev = []
for devIdx in range(0, freenect.num_devices(ctx)):
    print "opening device %d" % devIdx
    dev.append(freenect.open_device(ctx, devIdx))
    if not dev:
        freenect.error_open_device()
 
print "Starting TILT Cycle"
for tilt in xrange(TILT_START, TILT_MAX+TILT_STEP, TILT_STEP):
    for sensor in dev:
        print "Setting TILT: ", tilt
        freenect.set_tilt_degs(sensor, tilt)
    time.sleep(1)
 
print "Starting TILT Cycle"
for tilt in xrange(TILT_MAX+TILT_STEP, TILT_START, (TILT_STEP * -1)):
    for sensor in dev:
        print "Setting TILT: ", tilt
        freenect.set_tilt_degs(sensor, tilt)
    time.sleep(1)
 
for sensor in dev:
    print "Resetting TILT"
    freenect.set_tilt_degs(sensor, -35)
