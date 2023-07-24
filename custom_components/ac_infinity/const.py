"""Constants for the AC Infinity integration."""

from homeassistant.const import Platform

DOMAIN = "ac_infinity"
PLATFORMS = [Platform.SENSOR]

DEVICE_MAC_ADDR = "deviceMacAddr"
DEVICE_LABEL = "deviceLabel"
DEVICE_PORTS = "devicePorts"
DEVICE_PORT_INDEX = "devicePortIndex"
DEVICE_PORT_LABEL = "devicePortLabel"

SENSOR_KEY_TEMPERATURE = "temperature"
SENSOR_KEY_HUMIDITY = "humidity"
SENSOR_KEY_VPD = "vpd"

SENSOR_PORT_PREFIX = "port"
SENSOR_PORT_KEY_INTENSITY = "intensity"
SENSOR_PORT_KEY_ONLINE = "online"