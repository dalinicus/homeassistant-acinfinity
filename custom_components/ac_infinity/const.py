"""Constants for the AC Infinity integration."""

from homeassistant.const import Platform

DOMAIN = "ac_infinity"
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.NUMBER]
HOST = "http://www.acinfinityserver.com"

# Device Metadata
DEVICE_KEY_DEVICE_ID = "devId"
DEVICE_KEY_DEVICE_NAME = "devName"
DEVICE_KEY_MAC_ADDR = "devMacAddr"
DEVICE_KEY_DEVICE_INFO = "deviceInfo"
DEVICE_KEY_PORTS = "ports"

# Device Port Metadata
DEVICE_PORT_KEY_PORT = "port"
DEVICE_PORT_KEY_NAME = "portName"

# Device Sensor Fields
DEVICE_KEY_TEMPERATURE = "temperature"
DEVICE_KEY_HUMIDITY = "humidity"
DEVICE_KEY_VAPOR_PRESSURE_DEFICIT = "vpdnums"

# Device Port Sensor Fields
DEVICE_PORT_KEY_SPEAK = "speak"
DEVICE_PORT_KEY_ONLINE = "online"
