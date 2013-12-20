#!/usr/bin/env python
import freenect
import time
import sys
 
if len(sys.argv) < 2:
	tilt = 0
else:
	tilt = int(sys.argv[1])
ctx = freenect.init()
print "Number of kinects: %d\n" % freenect.num_devices(ctx)
dev = []
for devIdx in range(0, freenect.num_devices(ctx)):
    print "opening device %d" % devIdx
    dev.append(freenect.open_device(ctx, devIdx))
    if not dev:
        freenect.error_open_device()
 
print "Setting tilt"
for sensor in dev:
    print "Setting TILT: ", tilt
    freenect.set_tilt_degs(sensor, tilt)
