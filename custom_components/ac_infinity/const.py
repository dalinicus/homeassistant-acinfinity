"""Constants for the AC Infinity integration."""

from homeassistant.const import Platform

MANUFACTURER = "AC Infinity"
DOMAIN = "ac_infinity"
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SELECT, Platform.NUMBER]
HOST = "http://www.acinfinityserver.com"

# devInfoListAll Device Fields
DEVICE_KEY_DEVICE_ID = "devId"
DEVICE_KEY_DEVICE_NAME = "devName"
DEVICE_KEY_MAC_ADDR = "devMacAddr"
DEVICE_KEY_DEVICE_INFO = "deviceInfo"
DEVICE_KEY_PORTS = "ports"
DEVICE_KEY_HW_VERSION = "hardwareVersion"
DEVICE_KEY_SW_VERSION = "firmwareVersion"
DEVICE_KEY_DEVICE_TYPE = "devType"
DEVICE_PORT_KEY_PORT = "port"
DEVICE_PORT_KEY_NAME = "portName"

# devInfoListAll Sensor Fields
SENSOR_KEY_TEMPERATURE = "temperature"
SENSOR_KEY_HUMIDITY = "humidity"
SENSOR_KEY_VPD = "vpdnums"
SENSOR_PORT_KEY_SPEAK = "speak"
SENSOR_PORT_KEY_ONLINE = "online"

# getdevModeSettingList Setting Fields
SETTING_KEY_ON_SPEED = "onSpead"
SETTING_KEY_OFF_SPEED = "offSpead"
SETTING_KEY_AT_TYPE = "atType"
