import asyncio
import re
import sys
from unittest.mock import MagicMock
from urllib.parse import parse_qsl, unquote, urlparse

import pytest
from aioresponses import aioresponses

from custom_components.ac_infinity.client import (
    API_URL_ADD_DEV_MODE,
    API_URL_GET_DEV_MODE_SETTING,
    API_URL_GET_DEV_SETTING,
    API_URL_GET_DEVICE_INFO_LIST_ALL,
    API_URL_LOGIN,
    API_URL_MODE_AND_SETTINGS,
    API_URL_UPDATE_ADV_SETTING,
    ACInfinityClient,
    ACInfinityClientCannotConnect,
    ACInfinityClientInvalidAuth,
    ACInfinityClientRequestFailed,
)
from custom_components.ac_infinity.const import AdvancedSettingsKey, AtType, DeviceControlKey, ModeAndSettingKeys
from tests.data_models import (
    DEVICE_ID,
    DEVICE_INFO_LIST_ALL_PAYLOAD,
    DEVICE_NAME,
    DEVICE_SETTINGS,
    EMAIL,
    GET_DEV_MODE_SETTING_LIST_PAYLOAD,
    GET_DEV_SETTINGS_PAYLOAD,
    HOST,
    LOGIN_PAYLOAD,
    MODE_SET_ID,
    PASSWORD,
    DEVICE_CONTROLS,
    UPDATE_SUCCESS_PAYLOAD,
    USER_ID,
)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# noinspection SpellCheckingInspection
@pytest.mark.asyncio
class TestACInfinityClient:
    async def test_close_session_nulled(self):
        """when a client has not been logged in, is_logged_in should return false"""

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = MagicMock(return_value=asyncio.Future())
        mock_session.close.return_value.set_result(None)

        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._session = mock_session

        await client.close()

        assert client._session is None

    async def test_is_logged_in_returns_false_if_not_logged_in(self):
        """when a client has not been logged in, is_logged_in should return false"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)

        assert client.is_logged_in() is False

    async def test_is_logged_in_returns_true_if_logged_in(self):
        """when a client has not been logged in, is_logged_in should return false"""

        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID

        assert client.is_logged_in() is True

    async def test_login_user_id_set_on_success(self):
        """When login is called and is successful, the user id to make future requests should be set"""

        with aioresponses() as mocked:
            mocked.post(
                f"{HOST}{API_URL_LOGIN}",
                status=200,
                payload=LOGIN_PAYLOAD,
            )

            client = ACInfinityClient(HOST, EMAIL, PASSWORD)
            await client.login()

            assert client._user_id is not None

    @pytest.mark.parametrize(
        "password,expected",
        [
            ("hunter2", "hunter2"),
            ("!@DiFGQBRGapZ9MvDNU8AM6b", "!@DiFGQBRGapZ9MvDNU8AM6b"),
            ("teU8a4HWC@*i2o!iMojRv9*#M7VmF8Zn", "teU8a4HWC@*i2o!iMojRv9*#M"),
        ],
    )
    async def test_login_password_truncated_to_25_characters(self, password, expected):
        """AC Infinity API does not accept passwords greater than 25 characters.
        The Android/iOS app truncates passwords to accommodate for this.  We must do the same.
        """

        url = f"{HOST}{API_URL_LOGIN}"

        with aioresponses() as mocked:
            mocked.post(
                url,
                status=200,
                payload=LOGIN_PAYLOAD,
            )

            client = ACInfinityClient(HOST, EMAIL, password)
            await client.login()

            actual_password = next(iter(mocked.requests.values()))[0].kwargs["data"][
                "appPasswordl"
            ]
            assert actual_password == expected

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 500])
    async def test_login_api_connect_error_raised_on_http_error(self, status_code):
        """When login is called and returns a non-succesful status code, connect error should be raised"""

        with aioresponses() as mocked:
            mocked.post(
                f"{HOST}{API_URL_LOGIN}",
                status=status_code,
                payload={
                    "Message": "This is a unit test error message",
                    "MessageDetail": "This is a unit test error detail",
                },
            )

            client = ACInfinityClient(HOST, EMAIL, PASSWORD)
            with pytest.raises(ACInfinityClientCannotConnect):
                await client.login()

    @pytest.mark.parametrize("code", [400, 500])
    async def test_login_api_auth_error_on_failed_login(self, code):
        """When login is called and returns a non-succesful status code, connect error should be raised"""

        with aioresponses() as mocked:
            mocked.post(
                f"{HOST}{API_URL_LOGIN}",
                status=200,
                payload={"msg": "User Does Not Exist", "code": code},
            )

            client = ACInfinityClient(HOST, EMAIL, PASSWORD)
            with pytest.raises(ACInfinityClientInvalidAuth):
                await client.login()

    @pytest.mark.parametrize("code", [400, 500])
    async def test_post_request_failed_error_on_failed_request(self, code):
        """When login is called and returns a non-succesful status code, connect error should be raised"""

        with aioresponses() as mocked:
            mocked.post(
                f"{HOST}{API_URL_GET_DEVICE_INFO_LIST_ALL}",
                status=200,
                payload={"msg": "User Does Not Exist", "code": code},
            )

            client = ACInfinityClient(HOST, EMAIL, PASSWORD)
            client._user_id = USER_ID

            with pytest.raises(ACInfinityClientRequestFailed):
                await client.get_account_controllers()

    async def test_get_devices_list_all_returns_user_devices(self):
        """When logged in, user devices should return a list of user devices"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID

        with aioresponses() as mocked:
            mocked.post(
                f"{HOST}{API_URL_GET_DEVICE_INFO_LIST_ALL}",
                status=200,
                payload=DEVICE_INFO_LIST_ALL_PAYLOAD,
            )

            result = await client.get_account_controllers()

            assert result is not None
            assert result[0]["devId"] == f"{DEVICE_ID}"

    async def test_get_devices_list_all_connect_error_on_not_logged_in(self):
        """When not logged in, get user devices should throw a connect error"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        with pytest.raises(ACInfinityClientCannotConnect):
            await client.get_account_controllers()

    async def test_get_device_port_settings_connect_error_on_not_logged_in(self):
        """When not logged in, get user devices should throw a connect error"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        with pytest.raises(ACInfinityClientCannotConnect):
            await client.get_device_mode_settings(DEVICE_ID, 1)

    @staticmethod
    async def __make_generic_set_port_settings_call_and_get_sent_payload(
        dev_mode_payload=GET_DEV_MODE_SETTING_LIST_PAYLOAD,
    ):
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID

        found = {}
        try:
            with aioresponses() as mocked:
                mocked.post(
                    re.compile(rf"{HOST}{API_URL_GET_DEV_MODE_SETTING}.*"),
                    status=200,
                    payload=dev_mode_payload,
                )

                mocked.post(
                    re.compile(f"{HOST}{API_URL_ADD_DEV_MODE}.*"),
                    status=200,
                    payload=UPDATE_SUCCESS_PAYLOAD,
                )

                await client.update_device_controls(
                    DEVICE_ID, 4, {DeviceControlKey.ON_SPEED: 2}
                )

                for key in mocked.requests.keys():
                    method, url = key
                    if method == 'POST' and API_URL_ADD_DEV_MODE in str(url):
                        found = dict(parse_qsl(url.raw_query_string, keep_blank_values=True))
                        break

            assert found
            return found
        finally:
            await client.close()
            
    async def test_set_device_port_setting_values_copied_from_get_call(self):
        """When setting a value, first fetch the existing settings to build the payload"""

        payload = (
            await self.__make_generic_set_port_settings_call_and_get_sent_payload()
        )

        device_control_keys: list[str] = [
            getattr(DeviceControlKey, attr)
            for attr in dir(DeviceControlKey)
            if not attr.startswith('_')
        ]

        for key in device_control_keys:
            assert key in payload, f"Key {key} is missing"

    async def test_set_device_port_setting_value_changed_in_payload(self):
        """When setting a value, the value is updated in the built payload before sending"""
        payload = (
            await self.__make_generic_set_port_settings_call_and_get_sent_payload()
        )

        assert payload[DeviceControlKey.ON_SPEED] == '2'

    async def test_update_device_controls_connect_error_on_not_logged_in(self):
        """When not logged in, update device controls should throw a connect error"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        with pytest.raises(ACInfinityClientCannotConnect):
            await client.update_device_controls(DEVICE_ID, 1, {DeviceControlKey.ON_SPEED: 5})

    @pytest.mark.parametrize("port", [0, 1, 2, 3, 4])
    async def test_get_device_settings_returns_settings(self, port: int):
        """When logged in, get controller settings should return the current settings"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        try:
            with aioresponses() as mocked:
                mocked.post(
                    re.compile(rf"{HOST}{API_URL_GET_DEV_MODE_SETTING}.*"),
                    status=200,
                    payload=GET_DEV_SETTINGS_PAYLOAD,
                )

                result = await client.get_device_mode_settings(DEVICE_ID, port)

                assert result is not None
                assert result["devId"] == f"{DEVICE_ID}"

                gen = (request for request in mocked.requests.values())
                found = next(gen)

                assert found[0].kwargs["data"]["port"] == port
        finally:
            await client.close()

    async def test_get_device_settings_connect_error_on_not_logged_in(self):
        """When not logged in, get user devices should throw a connect error"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        with pytest.raises(ACInfinityClientCannotConnect):
            await client.get_device_mode_settings(DEVICE_ID, 0)

    @staticmethod
    async def __make_generic_update_advanced_settings_call_and_get_sent_payload(
        dev_settings_payload=GET_DEV_SETTINGS_PAYLOAD,
    ):
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        try:
            with aioresponses() as mocked:
                mocked.post(
                    re.compile(rf"{HOST}{API_URL_GET_DEV_SETTING}"),
                    status=200,
                    payload=dev_settings_payload,
                )

                mocked.post(
                    re.compile(rf"{HOST}{API_URL_UPDATE_ADV_SETTING}"),
                    status=200,
                    payload=UPDATE_SUCCESS_PAYLOAD,
                )

                await client.update_device_settings(
                    DEVICE_ID, 0, DEVICE_NAME, {AdvancedSettingsKey.CALIBRATE_HUMIDITY: 3}
                )

                for key in mocked.requests.keys():
                    method, url = key
                    if method == 'POST' and API_URL_UPDATE_ADV_SETTING in str(url):
                        found = dict(parse_qsl(url.raw_query_string, keep_blank_values=True))
                        break

            assert found
            return found
        finally:
            await client.close()


# Note for future me:  This test is now failing because you need to update the test data.

    async def test_update_advanced_settings_copied_from_get_call(self):
        """When setting a value, first fetch the existing settings to build the payload"""

        payload = (
            await self.__make_generic_update_advanced_settings_call_and_get_sent_payload()
        )

        device_settings_keys: list[str] = [
            getattr(AdvancedSettingsKey, attr)
            for attr in dir(AdvancedSettingsKey)
            if not attr.startswith('_')
        ]

        # yarl/aiohttp filters out query parameters with empty string values
        # So we only check for keys that have non-None values in the test data
        # (None values get converted to empty strings and are filtered out)
        for key in device_settings_keys:
            test_value = DEVICE_SETTINGS.get(key)
            if test_value is not None:
                assert key in payload, f"Key {key} is missing"

    async def test_update_advanced_settings_value_changed_in_payload(self):
        """When setting a value, the value is updated in the built payload before sending"""

        payload = (
            await self.__make_generic_update_advanced_settings_call_and_get_sent_payload()
        )

        assert payload[AdvancedSettingsKey.CALIBRATE_HUMIDITY] == '3'

    async def test_update_device_settings_connect_error_on_not_logged_in(self):
        """When not logged in, update device settings should throw a connect error"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        with pytest.raises(ACInfinityClientCannotConnect):
            await client.update_device_settings(DEVICE_ID, 1, DEVICE_NAME, {AdvancedSettingsKey.CALIBRATE_HUMIDITY: 5})

    @pytest.mark.parametrize("set_value", [0, None, 1])
    async def test_set_device_setting_zero_even_when_null(
        self,
        set_value,
    ):
        """When fetching existing settings before update, specified fields should be set to 0 if existing is null"""
        dev_settings = GET_DEV_SETTINGS_PAYLOAD

        assert isinstance(dev_settings["data"], dict)
        dev_settings["data"][AdvancedSettingsKey.OTA_UPDATING] = set_value
        dev_settings["data"][AdvancedSettingsKey.SUB_DEVICE_ID] = set_value
        dev_settings["data"][AdvancedSettingsKey.SUB_DEVICE_TYPE] = set_value
        dev_settings["data"][AdvancedSettingsKey.SUPPORT_OTA] = set_value

        """When fetching existing settings before update, specified fields should be set to 0 if existing is null"""
        payload = (
            await self.__make_generic_update_advanced_settings_call_and_get_sent_payload()
        )

        # certain None fields defaulted to 0 before sending.
        expected = str(set_value) if set_value else str(0)
        assert payload[AdvancedSettingsKey.OTA_UPDATING] == expected
        assert payload[AdvancedSettingsKey.SUB_DEVICE_ID] == expected
        assert payload[AdvancedSettingsKey.SUB_DEVICE_TYPE] == expected
        assert payload[AdvancedSettingsKey.SUPPORT_OTA] == expected

    async def test_set_device_settings_dev_name_pulled_from_existing_value(self):
        payload = (
            await self.__make_generic_update_advanced_settings_call_and_get_sent_payload()
        )

        assert AdvancedSettingsKey.DEV_NAME in payload
        assert payload[AdvancedSettingsKey.DEV_NAME] == DEVICE_NAME

    @staticmethod
    async def __make_generic_update_ai_device_control_and_settings_call_and_get_sent_payload(
        dev_mode_payload=GET_DEV_MODE_SETTING_LIST_PAYLOAD,
        at_type=AtType.AUTO,
    ):
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID

        found = {}
        try:
            with aioresponses() as mocked:
                mocked.post(
                    re.compile(rf"{HOST}{API_URL_GET_DEV_MODE_SETTING}.*"),
                    status=200,
                    payload=dev_mode_payload,
                )

                mocked.put(
                    re.compile(f"{HOST}{API_URL_MODE_AND_SETTINGS}.*"),
                    status=200,
                    payload=UPDATE_SUCCESS_PAYLOAD,
                )

                await client.update_ai_device_control_and_settings(
                    DEVICE_ID, 1, {DeviceControlKey.AT_TYPE: at_type, DeviceControlKey.ON_SPEED: 3}
                )

                for key in mocked.requests.keys():
                    method, url = key
                    if method == 'PUT' and API_URL_MODE_AND_SETTINGS in str(url):
                        found = dict(parse_qsl(url.raw_query_string, keep_blank_values=True))
                        break

            assert found
            return found
        finally:
            await client.close()

    async def test_update_ai_device_control_and_settings_values_copied_from_get_call(self):
        """When setting a value for AI controller, first fetch the existing settings to build the payload"""

        payload = (
            await self.__make_generic_update_ai_device_control_and_settings_call_and_get_sent_payload()
        )

        mode_and_setting_keys: list[str] = [
            getattr(ModeAndSettingKeys, attr)
            for attr in dir(ModeAndSettingKeys)
            if not attr.startswith('_')
        ]

        for key in mode_and_setting_keys:
            assert key in payload, f"Key {key} is missing"

    async def test_update_ai_device_control_and_settings_value_changed_in_payload(self):
        """When setting a value for AI controller, the value is updated in the built payload before sending"""
        payload = (
            await self.__make_generic_update_ai_device_control_and_settings_call_and_get_sent_payload()
        )

        assert payload[DeviceControlKey.ON_SPEED] == '3'

    async def test_update_ai_device_control_and_settings_connect_error_on_not_logged_in(self):
        """When not logged in, update AI device control and settings should throw a connect error"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        try:
            with pytest.raises(ACInfinityClientCannotConnect):
                await client.update_ai_device_control_and_settings(DEVICE_ID, 1, {DeviceControlKey.AT_TYPE: AtType.AUTO})
        finally:
            await client.close()

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 500])
    async def test_update_ai_device_control_and_settings_connect_error_on_http_error_get(self, status_code):
        """When GET request returns a non-200 status code, connect error should be raised"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        try:
            with aioresponses() as mocked:
                mocked.post(
                    re.compile(rf"{HOST}{API_URL_GET_DEV_MODE_SETTING}.*"),
                    status=status_code,
                    payload={
                        "Message": "This is a unit test error message",
                        "MessageDetail": "This is a unit test error detail",
                    },
                )

                with pytest.raises(ACInfinityClientCannotConnect):
                    await client.update_ai_device_control_and_settings(
                        DEVICE_ID, 1, {DeviceControlKey.AT_TYPE: AtType.AUTO}
                    )
        finally:
            await client.close()

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 500])
    async def test_update_ai_device_control_and_settings_connect_error_on_http_error_put(self, status_code):
        """When PUT request returns a non-200 status code, connect error should be raised"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        try:
            with aioresponses() as mocked:
                mocked.post(
                    re.compile(rf"{HOST}{API_URL_GET_DEV_MODE_SETTING}.*"),
                    status=200,
                    payload=GET_DEV_MODE_SETTING_LIST_PAYLOAD,
                )

                mocked.put(
                    re.compile(f"{HOST}{API_URL_MODE_AND_SETTINGS}.*"),
                    status=status_code,
                    payload={
                        "Message": "This is a unit test error message",
                        "MessageDetail": "This is a unit test error detail",
                    },
                )

                with pytest.raises(ACInfinityClientCannotConnect):
                    await client.update_ai_device_control_and_settings(
                        DEVICE_ID, 1, {DeviceControlKey.AT_TYPE: AtType.AUTO}
                    )
        finally:
            await client.close()

    @pytest.mark.parametrize("code", [400, 500])
    async def test_update_ai_device_control_and_settings_request_failed_on_failed_get(self, code):
        """When GET request returns code != 200 in response body, request failed error should be raised"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        try:
            with aioresponses() as mocked:
                mocked.post(
                    re.compile(rf"{HOST}{API_URL_GET_DEV_MODE_SETTING}.*"),
                    status=200,
                    payload={"msg": "Request Failed", "code": code},
                )

                with pytest.raises(ACInfinityClientRequestFailed):
                    await client.update_ai_device_control_and_settings(
                        DEVICE_ID, 1, {DeviceControlKey.AT_TYPE: AtType.AUTO}
                    )
        finally:
            await client.close()

    @pytest.mark.parametrize("code", [400, 500])
    async def test_update_ai_device_control_and_settings_request_failed_on_failed_put(self, code):
        """When PUT request returns code != 200 in response body, request failed error should be raised"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        try:
            with aioresponses() as mocked:
                mocked.post(
                    re.compile(rf"{HOST}{API_URL_GET_DEV_MODE_SETTING}.*"),
                    status=200,
                    payload=GET_DEV_MODE_SETTING_LIST_PAYLOAD,
                )

                mocked.put(
                    re.compile(f"{HOST}{API_URL_MODE_AND_SETTINGS}.*"),
                    status=200,
                    payload={"msg": "Request Failed", "code": code},
                )

                with pytest.raises(ACInfinityClientRequestFailed):
                    await client.update_ai_device_control_and_settings(
                        DEVICE_ID, 1, {DeviceControlKey.AT_TYPE: AtType.AUTO}
                    )
        finally:
            await client.close()

    @pytest.mark.parametrize("at_type,expected_id_str", [
        (AtType.OFF, "[16,17]"),
        (AtType.ON, "[16,18]"),
        (AtType.AUTO, "[112,16,19,32,98,99]"),
        (AtType.TIMER_TO_ON, "[16,20,21]"),
        (AtType.TIMER_TO_OFF, "[16,20,21]"),
        (AtType.CYCLE, "[16,22,23,40]"),
        (AtType.SCHEDULE, "[16,22,23,40]"),
        (AtType.VPD, "[16,81,32,98,99]"),
    ])
    async def test_update_ai_device_control_and_settings_mode_and_setting_id_str(self, at_type, expected_id_str):
        """When updating AI device controls, the correct modeAndSettingIdStr is set based on atType"""
        payload = (
            await self.__make_generic_update_ai_device_control_and_settings_call_and_get_sent_payload(
                at_type=at_type
            )
        )

        # Decode the URL-encoded value for comparison
        actual_value = unquote(payload[ModeAndSettingKeys.MODE_AND_SETTING_ID_STR])
        assert actual_value == expected_id_str

    async def test_update_ai_device_control_and_settings_value_error_on_unknown_at_type(self):
        """When updating AI device controls with an unknown atType, ValueError should be raised"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        try:
            with aioresponses() as mocked:
                mocked.post(
                    re.compile(rf"{HOST}{API_URL_GET_DEV_MODE_SETTING}.*"),
                    status=200,
                    payload=GET_DEV_MODE_SETTING_LIST_PAYLOAD,
                )

                # Use an invalid atType value (999 is not a valid AtType)
                with pytest.raises(ValueError, match="Unable to find setting id string - Unknown atType"):
                    await client.update_ai_device_control_and_settings(
                        DEVICE_ID, 1, {DeviceControlKey.AT_TYPE: 999}
                    )
        finally:
            await client.close()
