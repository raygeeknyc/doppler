import time
import collections

l = collections.deque()
start = time.time()
for a in range(0, 1024):
	for b in range(0, 1024):
		l.append(a*b)
	while len(l) > 0:
		l.popleft()
print 'Time for deque: %f' % (time.time() - start)
l = []
start = time.time()
for a in range(0, 1024):
	for b in range(0, 1024):
		l.append(a*b)
for c in l:
	pass
c = []
print 'Time for list: %f' % (time.time() - start)
