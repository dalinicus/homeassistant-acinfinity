import logging
from typing import Tuple

import aiohttp
import async_timeout
from homeassistant.exceptions import HomeAssistantError

from custom_components.ac_infinity.const import AdvancedSettingsKey, PortControlKey

_LOGGER = logging.getLogger(__name__)

API_URL_LOGIN = "/api/user/appUserLogin"
API_URL_GET_DEVICE_INFO_LIST_ALL = "/api/user/devInfoListAll"
API_URL_GET_DEV_MODE_SETTING = "/api/dev/getdevModeSettingList"
API_URL_ADD_DEV_MODE = "/api/dev/addDevMode"
API_URL_GET_DEV_SETTING = "/api/dev/getDevSetting"
API_URL_UPDATE_ADV_SETTING = "/api/dev/updateAdvSetting"


class ACInfinityClient:
    """Encapsulates http calls to the AC Infinity API"""

    def __init__(self, host: str, email: str, password: str) -> None:
        """
        Args:
            host: The base host of the AC Infinity API
            email: The e-mail to log in as, as configured by the user via config_flow
            password: The password to log in with, as configured by the user via config_flow
        """
        self._host = host
        self._email = email
        self._password = password

        self._user_id: (str | None) = None

    async def login(self):
        """Call the log in endpoint with the configured email and password, and obtain the user id to use for subsequent calls"""
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
        """returns true if the user id is set, false otherwise"""
        return True if self._user_id else False

    async def get_devices_list_all(self):
        """Obtains a list of controllers, including metadata and some sensor values.
        Does not include information related to settings.
        """
        if not self.is_logged_in():
            raise ACInfinityClientCannotConnect("AC Infinity client is not logged in.")

        headers = self.__create_headers(use_auth_token=True)
        json = await self.__post(
            API_URL_GET_DEVICE_INFO_LIST_ALL, {"userId": self._user_id}, headers
        )
        return json["data"]

    async def get_device_mode_settings_list(self, device_id: (str | int), port_id: int):
        """Obtains the settings for a particular port on a controller, which includes information
        like speed, sensor triggers, mode timers, etc...

        Args:
            device_id: The parent controller id of the port
            port_id: The port on the controller of the settings list to grab
        """
        if not self.is_logged_in():
            raise ACInfinityClientCannotConnect("AC Infinity client is not logged in.")

        headers = self.__create_headers(use_auth_token=True)
        json = await self.__post(
            API_URL_GET_DEV_MODE_SETTING, {"devId": device_id, "port": port_id}, headers
        )
        return json["data"]

    async def set_device_mode_settings(
        self, device_id: (str | int), port_id: int, key_values: list[Tuple[str, int]]
    ):
        """Sets the provided settings on a port to a new values

        Args:
            device_id: The parent controller id of port
            port_id: The port on the controller you want to set setting values for
            key_values: The key value pairs of settings to set
        """
        settings = await self.get_device_mode_settings_list(device_id, port_id)

        # Remove fields that are not part of update payload, as well as the devSettings structure so we're not messing
        # with the controller settings.
        for key in [
            PortControlKey.DEVICE_MAC_ADDR,
            PortControlKey.IPC_SETTING,
            PortControlKey.DEV_SETTING,
        ]:
            if key in settings:
                del settings[key]

        # Add defaulted fields that exist in the update call on the phone app, but may not exist in the fetch call
        for key in [
            PortControlKey.VPD_STATUS,
            PortControlKey.VPD_NUMS,
        ]:
            if key not in settings:
                settings[key] = 0

        # Convert ids that are strings on the fetch call to int values for the update call
        settings[PortControlKey.DEV_ID] = int(settings[PortControlKey.DEV_ID])
        settings[PortControlKey.MODE_SET_ID] = int(settings[PortControlKey.MODE_SET_ID])

        # Set values changed by the user
        for key, value in key_values:
            settings[key] = int(value)

        # Set any values that are None to 0 as that's what the update endpoint expects.
        for key in settings:
            if settings[key] is None:
                settings[key] = 0

        headers = self.__create_headers(use_auth_token=True)
        _ = await self.__post(API_URL_ADD_DEV_MODE, settings, headers)

    async def get_device_settings(self, device_id: (str | int), port: int):
        """Gets the current values of controller specific settings;
        such as temperature, humidity, and vpd calibration values

        Args:
            device_id: The controller id of the settings to grab
            port: 0 for controller settings, or the port number for port settings
        """
        if not self.is_logged_in():
            raise ACInfinityClientCannotConnect("AC Infinity client is not logged in.")

        headers = self.__create_headers(use_auth_token=True)
        json = await self.__post(
            API_URL_GET_DEV_SETTING, {"devId": device_id, "port": port}, headers
        )
        return json["data"]

    async def update_advanced_settings(
        self,
        device_id: (str | int),
        port: int,
        device_name: str,
        key_values: list[Tuple[str, int]],
    ):
        """Sets a given controller setting to a new value

        Args:
            device_id: The device id of the controller to update
            port: 0 for controller settings, or the port number for port settings
            device_name: The current controller name value as it exists in the coordinator from the last refresh call.
            key_values: key value pairs of settings to update
        """
        settings = await self.get_device_settings(device_id, port)

        # the fetch call does not contain the device name. If we use the payload without setting device name,
        # the ac infinity api will change the name of the controller to "None".  We need to set it first before anything.
        settings[AdvancedSettingsKey.DEV_NAME] = device_name

        # remove fields not expected in the update payload, so we don't get a 400
        for key in [
            AdvancedSettingsKey.SET_ID,
            AdvancedSettingsKey.DEV_MAC_ADDR,
            AdvancedSettingsKey.PORT_RESISTANCE,
            AdvancedSettingsKey.DEV_TIME_ZONE,
            AdvancedSettingsKey.SENSOR_SETTING,
            AdvancedSettingsKey.SENSOR_TRANS_BUFF,
            AdvancedSettingsKey.SUB_DEVICE_VERSION,
            AdvancedSettingsKey.SEC_FUC_REPORT_TIME,
            AdvancedSettingsKey.UPDATE_ALL_PORT,
            AdvancedSettingsKey.CALIBRATION_TIME,
        ]:
            if key in settings:
                del settings[key]

        # Find string based fields that are null and set them to empty string.  Add any keys that don't exist.
        for key in [
            AdvancedSettingsKey.SENSOR_TRANS_BUFF_STR,
            AdvancedSettingsKey.SENSOR_SETTING_STR,
            AdvancedSettingsKey.PORT_PARAM_DATA,
            AdvancedSettingsKey.PARAM_SENSORS,
        ]:
            if key not in settings or settings[key] is None:
                settings[key] = ""

        # Add defaulted fields that exist in the update call on the phone app, but may not exist in the fetch call
        for key in [
            AdvancedSettingsKey.SENSOR_ONE_TYPE,
            AdvancedSettingsKey.IS_SHARE,
            AdvancedSettingsKey.TARGET_VPD_SWITCH,
            AdvancedSettingsKey.SENSOR_TWO_TYPE,
            AdvancedSettingsKey.ZONE_SENSOR_TYPE,
        ]:
            if key not in settings:
                settings[key] = 0

        # Convert ids that are strings on the fetch call to int values for the update call
        settings[AdvancedSettingsKey.DEV_ID] = int(settings[AdvancedSettingsKey.DEV_ID])

        # Set any values that are None to 0 as that's what the update endpoint expects.
        for key in settings:
            if settings[key] is None:
                settings[key] = 0

        # Set values changed by the user
        for key, value in key_values:
            settings[key] = int(value)

        headers = self.__create_headers(use_auth_token=True)
        _ = await self.__post(API_URL_UPDATE_ADV_SETTING, settings, headers)

    async def __post(self, path, post_data, headers):
        """generically make a post request to the AC Infinity API"""
        async with async_timeout.timeout(10), aiohttp.ClientSession(
            raise_for_status=False, headers=headers
        ) as session, session.post(f"{self._host}{path}", data=post_data) as response:
            if response.status != 200:
                raise ACInfinityClientCannotConnect

            json = await response.json()
            if path == API_URL_UPDATE_ADV_SETTING:
                _LOGGER.info(json)
            if json["code"] != 200:
                if path == API_URL_LOGIN:
                    raise ACInfinityClientInvalidAuth
                else:
                    raise ACInfinityClientRequestFailed(json)

            return json

    def __create_headers(self, use_auth_token: bool) -> dict:
        """Creates a header object to use in a request to the AC Infinity API"""
        # noinspection SpellCheckingInspection
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
