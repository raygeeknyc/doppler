import time
import collections

timings = [0,0,0]
for iter in range(5):
	start = time.time()
	for x in range(1,30000):
		l = []
		for y in range(1,10):
			l.append(x)
	timings[0] += time.time()-start
	start = time.time()
	for x in range(1,30000):
		l = collections.deque()
		for y in range(1,10):
			l.append(x)
	timings[1] += time.time()-start
	start = time.time()
	l = collections.deque()
	for x in range(1,30000):
		for y in range(1,10):
			l.append(x)
		l.clear()
	timings[2] += time.time()-start
print "lists took %f" % timings[0]
print "deq took %f" % timings[1]
print "deque took %f" % timings[2]
