import json
import logging
from urllib.parse import urlencode

import aiohttp
import async_timeout
from homeassistant.exceptions import HomeAssistantError

from custom_components.ac_infinity.const import (
    AdvancedSettingsKey,
    AtType,
    DeviceControlKey,
    ModeAndSettingKeys,
    ROOM_TO_ROOM_FAN_DIRECTION_ID_STR,
    ROOM_TO_ROOM_FAN_DISPLAY_SETTING_ID_STR,
    ROOM_TO_ROOM_FAN_DISPLAY_SETTING_KEYS,
    ROOM_TO_ROOM_FAN_MODE_ID_STR,
    ROOM_TO_ROOM_FAN_MODE_MANUAL_STEADY_ID_STR,
    ROOM_TO_ROOM_FAN_POWER_ACTION_ID_STR,
    ROOM_TO_ROOM_FAN_UNSENT_KEYS,
    RoomToRoomFanExtraKeys,
    RoomToRoomFanMode,
)

_LOGGER = logging.getLogger(__name__)

API_URL_LOGIN = "/api/user/appUserLogin"
API_URL_GET_DEVICE_INFO_LIST_ALL = "/api/user/devInfoListAll"
API_URL_GET_DEV_MODE_SETTING = "/api/dev/getdevModeSettingList"
API_URL_ADD_DEV_MODE = "/api/dev/addDevMode"
API_URL_MODE_AND_SETTINGS = "/api/dev/modeAndSetting"
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
        self._user_id: str | None = None
        self._session: aiohttp.ClientSession | None = None

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

    def __ensure_logged_in(self) -> None:
        """Raise when a request requires an authenticated client."""
        if not self.is_logged_in():
            raise ACInfinityClientCannotConnect("AC Infinity client is not logged in.")

    async def get_account_controllers(self):
        """Obtains a list of controllers, including metadata and some sensor values.
        Does not include information related to settings.
        """
        self.__ensure_logged_in()

        headers = self.__create_headers(use_auth_token=True)
        body = await self.__post(
            API_URL_GET_DEVICE_INFO_LIST_ALL, {"userId": self._user_id}, headers
        )
        return body["data"]

    async def get_device_mode_settings(self, controller_id: str | int, device_port: int):
        """Obtains the settings for a particular port on a controller, which includes information
        like speed, sensor triggers, mode timers, etc...

        Args:
            controller_id: The parent controller id of the port
            device_port: The port on the controller of the settings list to grab
        """
        self.__ensure_logged_in()

        headers = self.__create_headers(use_auth_token=True)
        body = await self.__post(
            API_URL_GET_DEV_MODE_SETTING, {"devId": controller_id, "port": device_port}, headers
        )
        return body["data"]

    @staticmethod
    def __transfer_values(device_control_keys: list[str], new_values: dict, existing_values: dict):
        updated: dict[str, str | int | bool] = {}
        for key in device_control_keys:
            value = new_values.get(key, existing_values.get(key, 0))
            if value is None:
                updated[key] = 0
            elif isinstance(value, (dict, list)):
                updated[key] = json.dumps(value)
            elif isinstance(value, bool):
                updated[key] = str(value).lower()
            else:
                updated[key] = value

        return updated

    async def update_device_controls(
        self, controller_id: str | int, device_port: int, key_values: dict[str, int]
    ):
        """Sets the provided settings on a port to a new values

        Args:
            controller_id: The parent controller id
            device_port: The port on the controller the device is plugged into
            key_values: The key value pairs of settings to set
        """
        self.__ensure_logged_in()

        headers = self.__create_headers(use_auth_token=True)
        body = await self.__post(
            API_URL_GET_DEV_MODE_SETTING, {"devId": controller_id, "port": device_port}, headers
        )
        existing_values = body["data"]

        device_control_keys: list[str] = [
            getattr(DeviceControlKey, attr)
            for attr in dir(DeviceControlKey)
            if not attr.startswith('_')
        ]

        updated = self.__transfer_values(device_control_keys, key_values, existing_values)
        _ = await self.__post(f"{API_URL_ADD_DEV_MODE}?{urlencode(updated)}", None, headers)

    async def update_device_settings(
        self, controller_id: str | int, device_port: int, device_name: str, key_values: dict[str, int]
    ):
        """Sets the provided settings on a port to a new values

        Args:
            controller_id: The parent controller id
            device_port: The port on the controller the device is plugged into
            device_name: The name of the device
            key_values: The key value pairs of settings to set
        """
        self.__ensure_logged_in()

        headers = self.__create_headers(use_auth_token=True)
        body = await self.__post(
            API_URL_GET_DEV_SETTING, {"devId": controller_id, "port": device_port}, headers
        )
        existing_values = body["data"]

        device_settings_keys: list[str] = [
            getattr(AdvancedSettingsKey, attr)
            for attr in dir(AdvancedSettingsKey)
            if not attr.startswith('_')
        ]

        updated = self.__transfer_values(device_settings_keys, key_values, existing_values)
        updated[AdvancedSettingsKey.DEV_NAME] = device_name

        _ = await self.__post(f"{API_URL_UPDATE_ADV_SETTING}?{urlencode(updated)}", None, headers)

    async def update_ai_device_control_and_settings(
        self, controller_id: str | int, device_port: int, key_values: dict[str, int]
    ):
        """Sets the provided settings on a port to a new values

        Args:
            controller_id: id of the controller
            device_port: port of the device
            key_values: The key value pairs of settings to set
        """
        self.__ensure_logged_in()

        headers = self.__create_headers(use_auth_token=True, use_min_version=True)
        body = await self.__post(
            API_URL_GET_DEV_MODE_SETTING, {"devId": controller_id, "port": device_port}, headers
        )
        existing_values = body["data"]

        flattened = existing_values[DeviceControlKey.DEV_SETTING].copy()
        flattened.update(existing_values)

        device_control_keys: list[str] = [
            getattr(ModeAndSettingKeys, attr)
            for attr in dir(ModeAndSettingKeys)
            if not attr.startswith('_')
        ]

        updated = self.__transfer_values(device_control_keys, key_values, flattened)

        at_type = updated[DeviceControlKey.AT_TYPE]
        match at_type:
            case AtType.OFF:
                updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR] = "[16,17]"
            case AtType.ON:
                updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR] = "[16,18]"
            case AtType.AUTO:
                updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR] = "[112,16,19,32,98,99]"
            case AtType.TIMER_TO_ON | AtType.TIMER_TO_OFF:
                updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR] = "[16,20,21]"
            case AtType.CYCLE | AtType.SCHEDULE:
                updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR] = "[16,22,23,40]"
            case AtType.VPD:
                updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR] = "[16,81,32,98,99]"
            case _: # AtTypes from plugable AI Controller Sensors
                updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR] = "[16,97,32,98,99]"

        url = f"{API_URL_MODE_AND_SETTINGS}?{urlencode(updated)}"
        _ = await self.__put(url, headers)

    async def update_room_to_room_fan_control(
        self, controller_id: str | int, device_port: int, key_values: dict[str, int]
    ):
        """Sets control values for a room-to-room/through-wall fan (e.g. AC-TWT6, devType 33).

        These devices use the same /api/dev/modeAndSetting endpoint and response shape as
        AI controllers (a flat top-level payload merged with a nested "devSetting" object),
        but the "atType" mode values and their corresponding modeAndSettingIdStr strings are
        entirely different - confirmed via packet capture of the official app. See
        RoomToRoomFanMode and ROOM_TO_ROOM_FAN_MODE_ID_STR in const.py.

        Args:
            controller_id: id of the controller
            device_port: port of the device (always 0 for this device type)
            key_values: The key value pairs of settings to set
        """
        self.__ensure_logged_in()

        headers = self.__create_headers(use_auth_token=True, use_min_version=True)
        body = await self.__post(
            API_URL_GET_DEV_MODE_SETTING, {"devId": controller_id, "port": device_port}, headers
        )
        existing_values = body["data"]

        flattened = existing_values[DeviceControlKey.DEV_SETTING].copy()
        flattened.update(existing_values)
        previous_at_type = flattened.get(DeviceControlKey.AT_TYPE)

        # Includes RoomToRoomFanExtraKeys - fields this device's firmware requires that
        # aren't part of the general ModeAndSettingKeys set (omitting them
        # causes the API to reject the request with a generic failure code).
        device_control_keys: list[str] = [
            getattr(ModeAndSettingKeys, attr)
            for attr in dir(ModeAndSettingKeys)
            if not attr.startswith('_')
        ] + [
            getattr(RoomToRoomFanExtraKeys, attr)
            for attr in dir(RoomToRoomFanExtraKeys)
            if not attr.startswith('_')
        ]

        updated = self.__transfer_values(device_control_keys, key_values, flattened)

        # The official app never sends these on this device (confirmed via packet capture);
        # they exist in the shared key set for other controller types.
        for unused_key in ROOM_TO_ROOM_FAN_UNSENT_KEYS:
            updated.pop(unused_key, None)

        at_type = updated[DeviceControlKey.AT_TYPE]
        if at_type not in ROOM_TO_ROOM_FAN_MODE_ID_STR:
            raise ValueError(f"Unable to find setting id string - Unknown room-to-room fan atType {at_type}")

        # Confirmed via capture: a request that's specifically toggling power uses a fixed
        # idStr regardless of atType, distinct from mode/value changes which are keyed by
        # atType. Check the caller's original key_values (not the merged `updated`), since
        # every field is present in `updated` after merging with existing values.
        is_power_action = DeviceControlKey.POWER_STATE in key_values
        if is_power_action:
            updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR] = ROOM_TO_ROOM_FAN_POWER_ACTION_ID_STR
        elif set(key_values) == {DeviceControlKey.TOWARD}:
            updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR] = ROOM_TO_ROOM_FAN_DIRECTION_ID_STR
        elif set(key_values) == {DeviceControlKey.ON_SPEED} and at_type == previous_at_type:
            # Max fan speed adjusted on its own, in any mode
            updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR] = ROOM_TO_ROOM_FAN_MODE_MANUAL_STEADY_ID_STR
        elif at_type == RoomToRoomFanMode.MANUAL and at_type == previous_at_type:
            # Confirmed via capture: Manual mode is the one confirmed exception where
            # adjusting a value (fan speed) while already in the mode uses a different
            # idStr than entering the mode itself.
            updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR] = ROOM_TO_ROOM_FAN_MODE_MANUAL_STEADY_ID_STR
        else:
            updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR] = ROOM_TO_ROOM_FAN_MODE_ID_STR[at_type]

        _LOGGER.debug(
            "Room-to-room fan control update: previous_at_type=%s new_at_type=%s "
            "is_power_action=%s idStr=%s key_values=%s",
            previous_at_type, at_type, is_power_action,
            updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR], key_values,
        )

        url = f"{API_URL_MODE_AND_SETTINGS}?{urlencode(updated)}"
        _ = await self.__put(url, headers)

    async def update_room_to_room_fan_display_setting(
        self,
        controller_id: str | int,
        device_port: int,
        dev_name: str,
        inside_room_name: str,
        outside_room_name: str,
        key_values: dict[str, int],
    ):
        """Sets display/panel settings (backlight, keytone/keypress sound, brightness) for
        a room-to-room/through-wall fan (e.g. AC-TWT6, devType 33).

        Confirmed via packet capture: these use a fundamentally different, much smaller
        modeAndSetting payload than mode/fan-speed/power changes - built from the device's
        own "devSetting" object (from getdevModeSettingList) rather than the full
        ~172-field payload, plus a handful of identity fields (device/room names) that
        getdevModeSettingList doesn't return, so the caller must supply them (they're
        available from the cached controller properties).

        Args:
            controller_id: id of the controller
            device_port: port of the device (always 0 for this device type)
            dev_name: the controller's display name, as configured in the app
            inside_room_name: the "inside" zone's room name, as configured in the app
            outside_room_name: the "outside" zone's room name, as configured in the app
            key_values: The key value pairs of settings to set
        """
        self.__ensure_logged_in()

        headers = self.__create_headers(use_auth_token=True, use_min_version=True)
        body = await self.__post(
            API_URL_GET_DEV_MODE_SETTING, {"devId": controller_id, "port": device_port}, headers
        )
        existing_values = body["data"]

        flattened = existing_values[DeviceControlKey.DEV_SETTING].copy()
        flattened.update(existing_values)
        flattened["devName"] = dev_name
        flattened["insideRoomName"] = inside_room_name
        flattened["outsideRoomName"] = outside_room_name

        updated = self.__transfer_values(list(ROOM_TO_ROOM_FAN_DISPLAY_SETTING_KEYS), key_values, flattened)
        updated[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR] = ROOM_TO_ROOM_FAN_DISPLAY_SETTING_ID_STR

        _LOGGER.debug("Room-to-room fan display setting update: key_values=%s", key_values)

        url = f"{API_URL_MODE_AND_SETTINGS}?{urlencode(updated)}"
        _ = await self.__put(url, headers)

    async def close(self) -> None:
        """Close the session when done"""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def __get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(raise_for_status=False)
        return self._session

    async def __post(self, path, post_data, headers):
        """generically make a post request to the AC Infinity API"""
        session = await self.__get_session()
        async with async_timeout.timeout(10), session.post(
            f"{self._host}{path}", data=post_data, headers=headers
        ) as response:
            if response.status != 200:
                raise ACInfinityClientCannotConnect

            body = await response.json()
            if body["code"] != 200:
                if path == API_URL_LOGIN:
                    raise ACInfinityClientInvalidAuth
                else:
                    raise ACInfinityClientRequestFailed(body)

            return body

    async def __put(self, path, headers):
        """generically make a put request to the AC Infinity API"""
        session = await self.__get_session()
        async with async_timeout.timeout(10), session.put(
            f"{self._host}{path}", headers=headers
        ) as response:
            if response.status != 200:
                raise ACInfinityClientCannotConnect

            body = await response.json()
            if body["code"] != 200:
                raise ACInfinityClientRequestFailed(body)

            return body

    def __create_headers(self, use_auth_token: bool, use_min_version: bool = False) -> dict:
        """Creates a header object to use in a request to the AC Infinity API"""
        # noinspection SpellCheckingInspection
        headers: dict = {
            "User-Agent": "okhttp/4.12.0",
        }

        if use_auth_token:
            headers["token"] = self._user_id

        if use_min_version:
            headers["minversion"] = "3.5"

        return headers


class ACInfinityClientCannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class ACInfinityClientInvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class ACInfinityClientRequestFailed(HomeAssistantError):
    """Error to indicate a request failed"""
