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
ISSUE_URL = "https://github.com/dalinicus/homeassistant-acinfinity/issues/new?template=Blank+issue"


class CustomPortPropertyKey:
    # Derived sensors
    NEXT_STATE_CHANGE = "nextStateChange"


# noinspection SpellCheckingInspection
class ControllerPropertyKey:
    # /api/dev/devInfoListAll
    DEVICE_ID = "devId"
    DEVICE_NAME = "devName"
    MAC_ADDR = "devMacAddr"
    DEVICE_INFO = "deviceInfo"
    PORTS = "ports"
    HW_VERSION = "hardwareVersion"
    SW_VERSION = "firmwareVersion"
    DEVICE_TYPE = "devType"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    VPD = "vpdnums"
    ONLINE = "online"
    TIME_ZONE = "zoneId"
    SENSORS = "sensors"


class ControllerType:
    UIS_69_PRO = 11
    UIS_69_PRO_PLUS = 18
    UIS_89_AI_PLUS = 20


class SensorPropertyKey:
    # /api/dev/devInfoListAll via "sensors" property
    ACCESS_PORT = "accessPort"
    SENSOR_TYPE = "sensorType"
    SENSOR_UNIT = "sensorUnit"
    SENSOR_PRECISION = "sensorPrecision"
    SENSOR_DATA = "sensorData"


class SensorType:
    PROBE_TEMPERATURE_F = 0
    PROBE_TEMPERATURE_C = 1
    PROBE_HUMIDITY = 2
    PROBE_VPD = 3
    CONTROLLER_TEMPERATURE_F = 4
    CONTROLLER_TEMPERATURE_C = 5
    CONTROLLER_HUMIDITY = 6
    CONTROLLER_VPD = 7
    CO2 = 11
    LIGHT = 12


class SensorReferenceKey:
    # Sensor keys for known sensor values; arbitrary values not tied to the API data model.
    # Used to create unique keys for HASS entities.  Only valid for AI Controllers with the sensor usb ports.
    PROBE_TEMPERATURE = "probeTemperature"
    PROBE_HUMIDITY = "probeHumidity"
    PROBE_VPD = "probeVaporPressureDeficit"
    CONTROLLER_TEMPERATURE = "controllerTemperature"
    CONTROLLER_HUMIDITY = "controllerHumidity"
    CONTROLLER_VPD = "controllerVaporPressureDeficit"
    CO2_SENSOR = "co2Sensor"
    LIGHT_SENSOR = "lightSensor"


# noinspection SpellCheckingInspection
class PortPropertyKey:
    # /api/dev/devInfoListAll via "ports" property
    PORT = "port"
    NAME = "portName"
    SPEAK = "speak"
    ONLINE = "online"
    STATE = "loadState"
    REMAINING_TIME = "remainTime"


# noinspection SpellCheckingInspection
class AdvancedSettingsKey:
    # /api/dev/getDevSetting
    # /api/dev/updateAdvSetting
    DEV_ID = "devId"
    DEV_NAME = "devName"

    # fields associated with controller advanced settings
    TEMP_UNIT = "devCompany"
    CALIBRATE_TEMP = "devCt"
    CALIBRATE_TEMP_F = "devCth"
    CALIBRATE_HUMIDITY = "devCh"
    VPD_LEAF_TEMP_OFFSET = "vpdCt"
    VPD_LEAF_TEMP_OFFSET_F = "vpdCth"
    OUTSIDE_TEMP_COMPARE = "tempCompare"
    OUTSIDE_HUMIDITY_COMPARE = "humiCompare"

    # fields associated with port advanced settings
    DEVICE_LOAD_TYPE = "loadType"
    DYNAMIC_RESPONSE_TYPE = "isFlag"
    DYNAMIC_TRANSITION_TEMP = "devTt"
    DYNAMIC_TRANSITION_TEMP_F = "devTth"
    DYNAMIC_TRANSITION_HUMIDITY = "devTh"
    DYNAMIC_TRANSITION_VPD = "vpdTransition"
    DYNAMIC_BUFFER_TEMP = "devBt"
    DYNAMIC_BUFFER_TEMP_F = "devBth"
    DYNAMIC_BUFFER_HUMIDITY = "devBh"
    DYNAMIC_BUFFER_VPD = "devBvpd"
    SUNRISE_TIMER_ENABLED = "onTimeSwitch"
    SUNRISE_TIMER_DURATION = "onTime"

    # unassociated fields used for cleaning data
    CALIBRATION_TIME = "calibrationTime"
    SENSOR_SETTING = "sensorSetting"
    SENSOR_TRANS_BUFF = "sensorTransBuff"
    OTA_UPDATING = "otaUpdating"
    SUB_DEVICE_ID = "subDeviceId"
    SUB_DEVICE_TYPE = "subDeviceType"
    SUPPORT_OTA = "supportOta"
    SET_ID = "setId"
    DEV_MAC_ADDR = "devMacAddr"
    PORT_RESISTANCE = "portResistance"
    DEV_TIME_ZONE = "devTimeZone"
    PORT_PARAM_DATA = "portParamData"
    SUB_DEVICE_VERSION = "subDeviceVersion"
    SEC_FUC_REPORT_TIME = "secFucReportTime"
    UPDATE_ALL_PORT = "updateAllPort"
    SENSOR_TRANS_BUFF_STR = "sensorTransBuffStr"
    SENSOR_SETTING_STR = "sensorSettingStr"
    SENSOR_ONE_TYPE = "sensorOneType"
    IS_SHARE = "isShare"
    TARGET_VPD_SWITCH = "targetVpdSwitch"
    SENSOR_TWO_TYPE = "sensorTwoType"
    PARAM_SENSORS = "paramSensors"
    ZONE_SENSOR_TYPE = "zoneSensorType"


# noinspection SpellCheckingInspection
class PortControlKey:
    # /api/dev/getdevModeSettingsList
    # /api/dev/addDevMode
    DEV_ID = "devId"
    MODE_SET_ID = "modeSetid"
    SURPLUS = "surplus"
    ON_SPEED = "onSpead"
    OFF_SPEED = "offSpead"
    AT_TYPE = "atType"
    SCHEDULED_START_TIME = "schedStartTime"
    SCHEDULED_END_TIME = "schedEndtTime"
    TIMER_DURATION_TO_ON = "acitveTimerOn"
    TIMER_DURATION_TO_OFF = "acitveTimerOff"
    CYCLE_DURATION_ON = "activeCycleOn"
    CYCLE_DURATION_OFF = "activeCycleOff"
    VPD_SETTINGS_MODE = "vpdSettingMode"
    VPD_HIGH_ENABLED = "activeHtVpd"
    VPD_HIGH_TRIGGER = "activeHtVpdNums"
    VPD_LOW_ENABLED = "activeLtVpd"
    VPD_LOW_TRIGGER = "activeLtVpdNums"
    VPD_TARGET_ENABLED = "targetVpdSwitch"
    VPD_TARGET = "targetVpd"
    AUTO_SETTINGS_MODE = "settingMode"
    AUTO_TEMP_HIGH_TRIGGER = "devHt"
    AUTO_TEMP_HIGH_TRIGGER_F = "devHtf"
    AUTO_TEMP_HIGH_ENABLED = "activeHt"
    AUTO_HUMIDITY_HIGH_TRIGGER = "devHh"
    AUTO_HUMIDITY_HIGH_ENABLED = "activeHh"
    AUTO_TEMP_LOW_TRIGGER = "devLt"
    AUTO_TEMP_LOW_TRIGGER_F = "devLtf"
    AUTO_TEMP_LOW_ENABLED = "activeLt"
    AUTO_HUMIDITY_LOW_TRIGGER = "devLh"
    AUTO_HUMIDITY_LOW_ENABLED = "activeLh"
    AUTO_TARGET_TEMP_ENABLED = "targetTSwitch"
    AUTO_TARGET_TEMP = "targetTemp"
    AUTO_TARGET_TEMP_F = "targetTempF"
    AUTO_TARGET_HUMIDITY_ENABLED = "targetHumiSwitch"
    AUTO_TARGET_HUMIDITY = "targetHumi"
    EC_OR_TDS = "ecOrTds"
    VPD_STATUS = "vpdstatus"
    VPD_NUMS = "vpdnums"
    MASTER_PORT = "masterPort"
    DEVICE_MAC_ADDR = "devMacAddr"
    DEV_SETTING = "devSetting"
    IPC_SETTING = "ipcSetting"


# Schedules are not enabled or disabled by Booleans,
# but rather disabled when schedule time is set to 65535
SCHEDULE_DISABLED_VALUE = 65535  # Disabled
SCHEDULE_MIDNIGHT_VALUE = 0  # 12:00am, default for start time
SCHEDULE_EOD_VALUE = 1439  # 11:59pm, default for end time
