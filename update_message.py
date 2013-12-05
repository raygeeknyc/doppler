import string

#RENDERER_ADDRESS_BASE = "192.168.1."  # beaglexm
#RENDERER_ADDRESS_BASE_OCTET = 101     # beaglexm0
RENDERER_ADDRESS_BASE = "192.168.0."  # dweeno
RENDERER_ADDRESS_BASE_OCTET = 113     # dweeno
#RENDERER_ADDRESS_BASE = "127.0.0."  # octets ending in a dot
#RENDERER_ADDRESS_BASE_OCTET = 1
RENDERER_PORT = 5001
RENDERER_CONNECT_TIMEOUT_SECS = 2.0
MAXIMUM_RENDERER_CONNECT_RETRIES = 10 
SEND_CONFIG_COMMAND = "CONFIG?"

class CellState(object):
    CHANGE_RECEDE_SLOW = "r"
    CHANGE_RECEDE_FAST = "R"
    CHANGE_APPROACH_SLOW = "a"
    CHANGE_APPROACH_FAST = "A"
    CHANGE_REST = "s"
    CHANGE_STILL = "S"

    STATES = [
    CHANGE_RECEDE_SLOW,
    CHANGE_RECEDE_FAST,
    CHANGE_APPROACH_SLOW,
    CHANGE_APPROACH_FAST,
    CHANGE_REST,
    CHANGE_STILL]

class CellUpdate(object):
    def __init__(self, cell_state, coords):
      """state, (x,y)."""
      self._x = coords[0]
      self._y = coords[1]
      self._state = cell_state

    @property
    def state(self):
      return self._state

    @property
    def x(self):
      return self._x

    @property
    def y(self):
      return self._y

    @staticmethod
    def seriesToText(cellSeries):
	textUpdates = [cellUpdate.asText() for cellUpdate in cellSeries]
	return string.join(textUpdates,"|")
	  
    @staticmethod
    def fromText(text_update):
      """state,x,y"""
      try:
        (state,x,y) = text_update.split(",")
        return CellUpdate(state, (int(x), int(y)))
      except Exception as e:
	print "Error parsing text: %s" % str(e)
	return None

    def asText(self):
      return self._state+","+str(self._x)+","+str(self._y)
