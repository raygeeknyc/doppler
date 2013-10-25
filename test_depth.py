#!/usr/bin/env python
# arg = kinect device index, from 0
import copy
#import freenect
import numpy as np
import sys

THRESHOLD = 50

if len(sys.argv) != 2:
	print >> sys.stderr, "usage %s kinect-device-index" % sys.argv[0]
	sys.exit(255)

old_depth, timestamp = freenect.sync_get_depth()
print 'Kinect device %d, Depth[][] %d,%d\n' % (sys.argv[1], len(old_depth) ,len(old_depth[0]))
min_depth = None
max_depth = None
while 1:
    depth, timestamp = freenect.sync_get_depth(sys.argv[1])
    min_depth = min(depth)
    max_depth = max(depth)
    delta = []
    shifts = 0
    for row in range(0, len(depth)):
      delta.append([])
      for col in range(0, len(depth[row])):
        # print "%d,%d : %d -> %d = %d\n" % (row, col, int(old_depth[row][col]), int(depth[row][col]), int(old_depth[row][col]) - int(depth[row][col]))
        delta[row].append(int(old_depth[row][col]) - int(depth[row][col]))
        if abs(delta[row][col]) > THRESHOLD:
          shifts += 1
    print "%d shifts\n" % shifts
    old_depth = copy.deepcopy(depth)
