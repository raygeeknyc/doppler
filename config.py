# ADDRESS_BASE is the network on which the renderers listen
# ADDRESS_BASE_OCTET is the address of the first renderer, additional
# renderers increment this base octet sequentially.
#RENDERER_ADDRESS_BASE = "192.168.1."
#RENDERER_ADDRESS_BASE_OCTET = 101
RENDERER_ADDRESS_BASE = "127.0.0."
RENDERER_ADDRESS_BASE_OCTET = 1
# Every renderer listens on this port
RENDERER_PORT = 5001
RENDERER_CONNECT_TIMEOUT_SECS = 2.0
MAXIMUM_RENDERER_CONNECT_RETRIES = 10 
# We have 4 columns and 2 rows in the original installaton and
# 1 column and 1 row in the portable installation.
# ZONES=[4,2]
ZONES=[1,1]
# The maximum chunk of a config that a plotter receives from the first
# renderer at a time.
RENDERER_CONFIG_MAX_LENGTH = 512
