import collections
import time
import gc

a=collections.deque()
for x in range(10):
	a.append(str(x))
start = time.time()
for i in range(1000):
	if len(a):
		b = i
print "length took %f" % (time.time() - start)

gc.collect()
start = time.time()
for i in range(1000):
	if len(a) > 0:
		b = i
print "length test took %f" % (time.time() - start)
