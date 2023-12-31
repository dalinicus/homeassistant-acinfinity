HOST = "https://unittest.abcxyz"
EMAIL = "myemail@unittest.com"
PASSWORD = "hunter2"

USER_ID = "11763238626156107487"
DEVICE_ID = 54929097239553773072
DEVICE_NAME = "Grow Tent"
MAC_ADDR = "2B120D62DC00"

EMAIL = "myemail@unittest.com"
PASSWORD = "hunter2"
ENTRY_ID = f"ac_infinity-{EMAIL}"
POLLING_INTERVAL = 15

LOGIN_PAYLOAD = {
    "msg": "Success",
    "code": 200,
    "data": {
        "appId": USER_ID,
        "nickName": EMAIL,
        "appEmail": EMAIL,
        "appPasswordl": "286519e4331f486cbbef02180f5e2f",
        "appUsable": 1,
        "forumUsable": 1,
        "forumRole": 0,
        "appCreateTime": "2023-07-11 20:59:07",
        "appIsanalytics": 0,
        "appIsbugreport": 0,
        "appIsemailrepost": 0,
        "createTime": None,
    },
}

DEVICE_INFO = {
    "devId": str(DEVICE_ID),
    "devCode": "ABCDEFG",
    "devName": DEVICE_NAME,
    "devType": 11,
    "devAccesstime": 1692328784,
    "devPortCount": 4,
    "devOfftime": 1692328718,
    "devMacAddr": MAC_ADDR,
    "devVersion": 7,
    "online": 1,
    "isShare": 0,
    "devExternalList": None,
    "deviceInfo": {
        "devId": DEVICE_ID,
        "temperature": 2417,
        "temperatureF": 7551,
        "humidity": 7200,
        "tTrend": 0,
        "hTrend": 0,
        "unit": 0,
        "speak": 0,
        "trend": 0,
        "curMode": 3,
        "remainTime": None,
        "modeTye": 15,
        "advTriggerInfo": None,
        "notificationTrigger": None,
        "alertTrigger": None,
        "online": 1,
        "lkType": None,
        "endTime": 1692328718,
        "master": 0,
        "masterPort": 2,
        "allPortStatus": 7,
        "ports": [
            {
                "speak": 5,
                "deviceType": None,
                "trend": 0,
                "port": 1,
                "curMode": 7,
                "remainTime": 46545,
                "modeTye": 0,
                "online": 1,
                "portName": "Grow Lights",
                "portAccess": None,
                "portResistance": 3300,
                "isOpenAutomation": 0,
                "advUpdateTime": None,
                "loadType": 0,
                "loadState": 1,
                "abnormalState": 0,
                "overcurrentStatus": 0,
            },
            {
                "speak": 7,
                "deviceType": None,
                "trend": 0,
                "port": 2,
                "curMode": 2,
                "remainTime": None,
                "modeTye": 15,
                "online": 1,
                "portName": "Exhaust Fan",
                "portAccess": None,
                "portResistance": 5100,
                "isOpenAutomation": 0,
                "advUpdateTime": None,
                "loadType": 0,
                "loadState": 1,
                "abnormalState": 0,
                "overcurrentStatus": 0,
            },
            {
                "speak": 5,
                "deviceType": None,
                "trend": 0,
                "port": 3,
                "curMode": 2,
                "remainTime": None,
                "modeTye": 15,
                "online": 1,
                "portName": "Circulating Fan",
                "portAccess": None,
                "portResistance": 10000,
                "isOpenAutomation": 0,
                "advUpdateTime": None,
                "loadType": 0,
                "loadState": 1,
                "abnormalState": 0,
                "overcurrentStatus": 0,
            },
            {
                "speak": 0,
                "deviceType": None,
                "trend": 0,
                "port": 4,
                "curMode": 2,
                "remainTime": None,
                "modeTye": 15,
                "online": 0,
                "portName": "Port 4",
                "portAccess": None,
                "portResistance": 65535,
                "isOpenAutomation": 0,
                "advUpdateTime": None,
                "loadType": 0,
                "loadState": 0,
                "abnormalState": 0,
                "overcurrentStatus": 0,
            },
        ],
        "logCreateTime": None,
        "isOpenAutomation": 0,
        "advUpdateTime": None,
        "loadState": 0,
        "abnormalState": 0,
        "deviceInfoI": None,
        "tempCompare": 0,
        "humiCompare": 0,
        "ectdsType": None,
        "tdsUnit": None,
        "ecUnit": None,
        "sensorCount": None,
        "sensors": None,
        "overcurrentStatus": 0,
        "vpdnums": 83,
        "vpdstatus": 0,
    },
    "appEmail": EMAIL,
    "devTimeZone": "GMT+00:00",
    "createTime": None,
    "timeGMT": None,
    "timeZone": None,
    "firmwareVersion": "3.2.25",
    "hardwareVersion": "1.1",
    "workMode": 1,
    "zoneId": "America/Chicago",
    "wifiName": None,
}

DEVICE_SETTING = {
    "modeSetid": "1678871847944916993",
    "devId": "1424979258063355749",
    "externalPort": 4,
    "offSpead": 0,
    "onSpead": 5,
    "activeHt": 1,
    "devHt": 89,
    "devHtf": 193,
    "devLtf": 32,
    "activeLt": 0,
    "devLt": 0,
    "activeHh": 0,
    "devHh": 100,
    "activeLh": 0,
    "devLh": 0,
    "acitveTimerOn": 0,
    "acitveTimerOff": 0,
    "activeCycleOn": 0,
    "activeCycleOff": 0,
    "schedStartTime": 65535,
    "schedEndtTime": 65535,
    "surplus": None,
    "modeType": 15,
    "activeHtVpd": 0,
    "activeLtVpd": 0,
    "activeHtVpdNums": 99,
    "activeLtVpdNums": 1,
    "targetTSwitch": 0,
    "targetHumiSwitch": 0,
    "settingMode": 0,
    "vpdSettingMode": 0,
    "targetVpdSwitch": 0,
    "targetVpd": 0,
    "targetTemp": 0,
    "targetTempF": 32,
    "targetHumi": 0,
    "isUpdateVpdNums": False,
    "co2TargetSwitch": None,
    "co2SettingMode": None,
    "co2HighSwitch": None,
    "co2LowSwitch": None,
    "co2HighValue": None,
    "co2LowValue": None,
    "co2TargetValue": None,
    "co2FanTargetSwitch": None,
    "co2FanSettingMode": None,
    "co2FanHighSwitch": None,
    "co2FanLowSwitch": None,
    "co2FanHighValue": None,
    "co2FanLowValue": None,
    "co2FanTargetValue": None,
    "moistureTargetSwitch": None,
    "moistureSettingMode": None,
    "moistureHighSwitch": None,
    "moistureLowSwitch": None,
    "moistureHighValue": None,
    "moistureLowValue": None,
    "moistureTargetValue": None,
    "waterTempTargetSwitch": None,
    "waterTempSettingMode": None,
    "waterTempHighSwitch": None,
    "waterTempLowSwitch": None,
    "waterTempHighValueF": None,
    "waterTempHighValue": None,
    "waterTempLowValueF": None,
    "waterTempLowValue": None,
    "waterTempTargetValueF": None,
    "waterTempTargetValue": None,
    "phTargetSwitch": None,
    "phSettingMode": None,
    "phHighSwitch": None,
    "phLowSwitch": None,
    "phHighValue": None,
    "phLowValue": None,
    "phTargetValue": None,
    "ecTdsTargetSwitch": None,
    "ecTdsSettingMode": None,
    "ecTdsHighSwitch": None,
    "ecTdsLowSwitch": None,
    "ecTdsHighValueEc": None,
    "ecTdsHighValueTds": None,
    "ecTdsLowValueEc": None,
    "ecTdsLowValueTds": None,
    "ecTdsTargetValueEc": None,
    "ecTdsTargetValueTds": None,
    "humidity": 7709,
    "temperature": 2377,
    "tTrend": 0,
    "hTrend": 1,
    "unit": 0,
    "speak": 5,
    "trend": 0,
    "atType": 2,
    "temperatureF": 7479,
    "isOpenAutomation": 0,
    "devTimeZone": "GMT-05:00",
    "devSetting": {
        "setId": None,
        "devId": "1424979258063355749",
        "externalPort": 4,
        "devLight": 163,
        "hasBacklightSwitch": 1,
        "backlightSwitch": 1,
        "devCt": 0,
        "devCth": 0,
        "devCh": 0,
        "devTth": 0,
        "devTt": 0,
        "devTh": 0,
        "devCompany": 0,
        "vpdCth": 0,
        "vpdCt": 0,
        "vpdTransition": 0,
        "devBth": 0,
        "devBt": 0,
        "devBh": 0,
        "devBvpd": 0,
        "isFlag": 0,
        "onTimeSwitch": 0,
        "onTime": 0,
        "sensors": None,
        "isOpenDoseTime": None,
        "onDoseTime": None,
        "offDoseTime": None,
        "isOnMinMaxTime": None,
        "onMinTime": None,
        "onMaxTime": None,
        "ecOrTds": None,
        "ecUnit": None,
        "tdsUnit": None,
        "dualZoneSwitch": 1,
        "photoCellSwitch": 1,
    },
    "loadType": 0,
    "loadState": 1,
    "abnormalState": 0,
    "devMacAddr": None,
    "restore": False,
    "masterPort": None,
    "onlyUpdateSpeed": 0,
}

DEVICE_SETTINGS_PAYLOAD = {"msg": "操作成功", "code": 200, "data": DEVICE_SETTING}

DEVICE_SETTINGS = {
    str(DEVICE_ID): {
        1: DEVICE_SETTING,
        2: DEVICE_SETTING,
        3: DEVICE_SETTING,
        4: DEVICE_SETTING,
    }
}

DEVICE_INFO_LIST_ALL = [DEVICE_INFO]

DEVICE_INFO_DATA = {str(DEVICE_ID): DEVICE_INFO}

DEVICE_INFO_LIST_ALL_PAYLOAD = {
    "msg": "操作成功",
    "code": 200,
    "data": DEVICE_INFO_LIST_ALL,
}

ADD_DEV_MODE_PAYLOAD = {"msg": "操作成功", "code": 200}
