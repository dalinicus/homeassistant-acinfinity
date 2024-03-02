from typing import Tuple

import aiohttp
import async_timeout
from homeassistant.exceptions import HomeAssistantError

API_URL_LOGIN = "/api/user/appUserLogin"
API_URL_GET_DEVICE_INFO_LIST_ALL = "/api/user/devInfoListAll"
API_URL_GET_DEV_MODE_SETTING = "/api/dev/getdevModeSettingList"
API_URL_ADD_DEV_MODE = "/api/dev/addDevMode"


class ACInfinityClient:
    def __init__(self, host: str, email: str, password: str) -> None:
        self._host = host
        self._email = email
        self._password = password

        self._user_id: (str | None) = None

    async def login(self):
        headers = self.__create_headers(use_auth_token=False)

        # AC Infinity API does not accept passwords greater than 25 characters.
        # The Android/iOS app truncates passwords to accommodate for this.  We must do the same.
        normalized_password: str = self._password[0:25]

        response = await self.__post(
            API_URL_LOGIN,
            {"appEmail": self._email, "appPasswordl": normalized_password},
            headers,
        )
        self._user_id = response["data"]["appId"]

    def is_logged_in(self):
        return True if self._user_id else False

    async def get_all_device_info(self):
        if not self.is_logged_in():
            raise ACInfinityClientCannotConnect("AC Infinity client is not logged in.")

        headers = self.__create_headers(use_auth_token=True)
        json = await self.__post(
            API_URL_GET_DEVICE_INFO_LIST_ALL, {"userId": self._user_id}, headers
        )
        return json["data"]

    async def get_device_port_settings(self, device_id: (str | int), port_id: int):
        if not self.is_logged_in():
            raise ACInfinityClientCannotConnect("AC Infinity client is not logged in.")

        headers = self.__create_headers(use_auth_token=True)
        json = await self.__post(
            API_URL_GET_DEV_MODE_SETTING, {"devId": device_id, "port": port_id}, headers
        )
        return json["data"]

    async def set_device_port_settings(
        self, device_id: (str | int), port_id: int, keyValues: list[Tuple[str, int]]
    ):
        active_settings = await self.get_device_port_settings(device_id, port_id)
        payload = {
            "acitveTimerOff": active_settings["acitveTimerOff"],
            "acitveTimerOn": active_settings["acitveTimerOn"],
            "activeCycleOff": active_settings["activeCycleOff"],
            "activeCycleOn": active_settings["activeCycleOn"],
            "activeHh": active_settings["activeHh"],
            "activeHt": active_settings["activeHt"],
            "activeHtVpd": active_settings["activeHtVpd"],
            "activeHtVpdNums": active_settings["activeHtVpdNums"],
            "activeLh": active_settings["activeLh"],
            "activeLt": active_settings["activeLt"],
            "activeLtVpd": active_settings["activeLtVpd"],
            "activeLtVpdNums": active_settings["activeLtVpdNums"],
            "atType": active_settings["atType"],
            "devHh": active_settings["devHh"],
            "devHt": active_settings["devHt"],
            "devHtf": active_settings["devHtf"],
            "devId": active_settings["devId"],
            "devLh": active_settings["devLh"],
            "devLt": active_settings["devLt"],
            "devLtf": active_settings["devLtf"],
            "externalPort": active_settings["externalPort"],
            "hTrend": active_settings["hTrend"],
            "isOpenAutomation": active_settings["isOpenAutomation"],
            "onSpead": active_settings["onSpead"],
            "offSpead": active_settings["offSpead"],
            "onlyUpdateSpeed": active_settings["onlyUpdateSpeed"],
            "schedEndtTime": active_settings["schedEndtTime"],
            "schedStartTime": active_settings["schedStartTime"],
            "settingMode": active_settings["settingMode"],
            "surplus": active_settings["surplus"] or 0,
            "tTrend": active_settings["tTrend"],
            "targetHumi": active_settings["targetHumi"],
            "targetHumiSwitch": active_settings["targetHumiSwitch"] or 0,
            "targetTSwitch": active_settings["targetTSwitch"] or 0,
            "targetTemp": active_settings["targetTemp"],
            "targetTempF": active_settings["targetTempF"],
            "targetVpd": active_settings["targetVpd"],
            "targetVpdSwitch": active_settings["targetVpdSwitch"] or 0,
            "trend": active_settings["trend"],
            "unit": active_settings["unit"],
            "vpdSettingMode": active_settings["vpdSettingMode"],
        }

        for key, value in keyValues:
            payload[key] = int(value)

        headers = self.__create_headers(use_auth_token=True)
        _ = await self.__post(API_URL_ADD_DEV_MODE, payload, headers)

    async def __post(self, path, post_data, headers):
        async with async_timeout.timeout(10), aiohttp.ClientSession(
            raise_for_status=False, headers=headers
        ) as session, session.post(f"{self._host}{path}", data=post_data) as response:
            if response.status != 200:
                raise ACInfinityClientCannotConnect

            json = await response.json()
            if json["code"] != 200:
                if path == API_URL_LOGIN:
                    raise ACInfinityClientInvalidAuth
                else:
                    raise ACInfinityClientRequestFailed(json)

            return json

    def __create_headers(self, use_auth_token: bool) -> dict:
        headers: dict = {
            "User-Agent": "ACController/1.8.2 (com.acinfinity.humiture; build:489; iOS 16.5.1) Alamofire/5.4.4",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        }

        if use_auth_token:
            headers["token"] = self._user_id

        return headers


class ACInfinityClientCannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class ACInfinityClientInvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class ACInfinityClientRequestFailed(HomeAssistantError):
    """Error to indicate a request failed"""
