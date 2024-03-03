"""Constants for the AC Infinity integration."""

from homeassistant.const import Platform

MANUFACTURER = "AC Infinity"
DOMAIN = "ac_infinity"
PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.TIME,
    Platform.SWITCH,
]
HOST = "http://www.acinfinityserver.com"
CONF_POLLING_INTERVAL = "polling_interval"
CONF_UPDATE_PASSWORD = "update_password"
DEFAULT_POLLING_INTERVAL = 10

# devInfoListAll ReadOnly Device Fields
PROPERTY_KEY_DEVICE_ID = "devId"
PROPERTY_KEY_DEVICE_NAME = "devName"
PROPERTY_KEY_MAC_ADDR = "devMacAddr"
PROPERTY_KEY_DEVICE_INFO = "deviceInfo"
PROPERTY_KEY_PORTS = "ports"
PROPERTY_KEY_HW_VERSION = "hardwareVersion"
PROPERTY_KEY_SW_VERSION = "firmwareVersion"
PROPERTY_KEY_DEVICE_TYPE = "devType"
PROPERTY_PORT_KEY_PORT = "port"
PROPERTY_PORT_KEY_NAME = "portName"

# devInfoListAll Sensor State Fields
SENSOR_KEY_TEMPERATURE = "temperature"
SENSOR_KEY_HUMIDITY = "humidity"
SENSOR_KEY_VPD = "vpdnums"
SENSOR_PORT_KEY_SPEAK = "speak"
SENSOR_PORT_KEY_ONLINE = "online"

# getdevModeSettingsList Sensor Fields
SENSOR_SETTING_KEY_SURPLUS = "surplus"

# getdevModeSettingList Setting Fields
SETTING_KEY_ON_SPEED = "onSpead"
SETTING_KEY_OFF_SPEED = "offSpead"
SETTING_KEY_AT_TYPE = "atType"
SETTING_KEY_SCHEDULED_START_TIME = "schedStartTime"
SETTING_KEY_SCHEDULED_END_TIME = "schedEndtTime"
SETTING_KEY_TIMER_DURATION_TO_ON = "acitveTimerOn"
SETTING_KEY_TIMER_DURATION_TO_OFF = "acitveTimerOff"
SETTING_KEY_CYCLE_DURATION_ON = "activeCycleOn"
SETTING_KEY_CYCLE_DURATION_OFF = "activeCycleOff"
SETTING_KEY_VPD_HIGH_ENABLED = "activeHtVpd"
SETTING_KEY_VPD_HIGH_TRIGGER = "activeHtVpdNums"
SETTING_KEY_VPD_LOW_ENABLED = "activeLtVpd"
SETTING_KEY_VPD_LOW_TRIGGER = "activeLtVpdNums"
SETTING_KEY_AUTO_TEMP_HIGH_TRIGGER = "devHt"
SETTING_KEY_AUTO_TEMP_HIGH_TRIGGER_F = "devHtf"
SETTING_KEY_AUTO_TEMP_HIGH_ENABLED = "activeHt"
SETTING_KEY_AUTO_HUMIDITY_HIGH_TRIGGER = "devHh"
SETTING_KEY_AUTO_HUMIDITY_HIGH_ENABLED = "activeHh"
SETTING_KEY_AUTO_TEMP_LOW_TRIGGER = "devLt"
SETTING_KEY_AUTO_TEMP_LOW_TRIGGER_F = "devLtf"
SETTING_KEY_AUTO_TEMP_LOW_ENABLED = "activeLt"
SETTING_KEY_AUTO_HUMIDITY_LOW_TRIGGER = "devLh"
SETTING_KEY_AUTO_HUMIDITY_LOW_ENABLED = "activeLh"
SETTING_KEY_TARGET_HUMIDITY_SWITCH = "targetHumiSwitch"
SETTING_KEY_TARGET_TEMPERATURE_SWITCH = "targetTSwitch"
SETTING_KEY_TARGET_VPD_SWITCH = "targetVpdSwitch"

# Schedules are not enabled or disabled by Booleans,
# but rather disabled when schedule time is set to 65535
SCHEDULE_DISABLED_VALUE = 65535  # Disabled
SCHEDULE_MIDNIGHT_VALUE = 0  # 12:00am, default for start time
SCHEDULE_EOD_VALUE = 1439  # 11:59pm, default for end time
