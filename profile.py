import gc
import resource

def MemUsedKB():
    usage=resource.getrusage(resource.RUSAGE_SELF)
    return (usage[2]*resource.getpagesize())/1024.0

print "GC: %s" % gc.isenabled()
mem = MemUsedKB()
print "KB consumed: %f" % (MemUsedKB() - mem)
print "%d garbage objects" % len(gc.garbage)
print "%d tracked objects" % len(gc.get_objects())
for x in range(1024):
	pass
print "KB consumed: %f" % (MemUsedKB() - mem)
print "%d garbage objects" % len(gc.garbage)
print "%d tracked objects" % len(gc.get_objects())
for x in range(2048):
	xs = str(x)
print "KB consumed: %f" % (MemUsedKB() - mem)
print "%d garbage objects" % len(gc.garbage)
print "%d tracked objects" % len(gc.get_objects())
