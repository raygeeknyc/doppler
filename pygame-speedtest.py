import random
import pygame
import time
from pygame.locals import *

pygame.init()

displayInfo = pygame.display.Info()
displaySurface = pygame.display.set_mode((displayInfo.current_w, displayInfo.current_h),pygame.FULLSCREEN)
red = pygame.Color(255,0,0)
blue = pygame.Color(0,255,0)
green = pygame.Color(0,0,255)
colors = [red, green, blue]
xRes = displayInfo.current_w / 10
yRes = displayInfo.current_h / 10
start = time.time()
for x in range(xRes):
	for y in range(yRes):
		pygame.draw.rect(displaySurface, colors[random.randint(0,len(colors)-1)], (x*10, y*10, 10, 10))
pygame.display.update()
print '%d x %d took %f seconds' % (xRes, yRes,  (time.time() - start))
