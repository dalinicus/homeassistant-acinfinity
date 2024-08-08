import pytest
from aioresponses import aioresponses

from custom_components.ac_infinity.client import (
    API_URL_ADD_DEV_MODE,
    API_URL_GET_DEV_MODE_SETTING,
    API_URL_GET_DEV_SETTING,
    API_URL_GET_DEVICE_INFO_LIST_ALL,
    API_URL_LOGIN,
    API_URL_UPDATE_ADV_SETTING,
    ACInfinityClient,
    ACInfinityClientCannotConnect,
    ACInfinityClientInvalidAuth,
    ACInfinityClientRequestFailed,
)
from custom_components.ac_infinity.const import AdvancedSettingsKey, PortControlKey
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
    PORT_CONTROLS,
    UPDATE_SUCCESS_PAYLOAD,
    USER_ID,
)


# noinspection SpellCheckingInspection
@pytest.mark.asyncio
class TestACInfinityClient:
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

            mocked.assert_called_with(
                url,
                "POST",
                data={"appEmail": "myemail@unittest.com", "appPasswordl": expected},
            )

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
                await client.get_devices_list_all()

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

            result = await client.get_devices_list_all()

            assert result is not None
            assert result[0]["devId"] == f"{DEVICE_ID}"

    async def test_get_devices_list_all_connect_error_on_not_logged_in(self):
        """When not logged in, get user devices should throw a connect error"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        with pytest.raises(ACInfinityClientCannotConnect):
            await client.get_devices_list_all()

    async def test_get_device_port_settings_connect_error_on_not_logged_in(self):
        """When not logged in, get user devices should throw a connect error"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        with pytest.raises(ACInfinityClientCannotConnect):
            await client.get_device_mode_settings_list(DEVICE_ID, 1)

    @staticmethod
    async def __make_generic_set_port_settings_call_and_get_sent_payload(
        dev_mode_payload=GET_DEV_MODE_SETTING_LIST_PAYLOAD,
    ):
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        with aioresponses() as mocked:
            mocked.post(
                f"{HOST}{API_URL_GET_DEV_MODE_SETTING}",
                status=200,
                payload=dev_mode_payload,
            )

            mocked.post(
                f"{HOST}{API_URL_ADD_DEV_MODE}",
                status=200,
                payload=UPDATE_SUCCESS_PAYLOAD,
            )

            await client.set_device_mode_settings(
                DEVICE_ID, 4, [(PortControlKey.ON_SPEED, 2)]
            )

            gen = (request for request in mocked.requests.values())
            _ = next(gen)
            found = next(gen)

            return found[0].kwargs["data"]

    async def test_set_device_port_setting_values_copied_from_get_call(self):
        """When setting a value, first fetch the existing settings to build the payload"""

        payload = (
            await self.__make_generic_set_port_settings_call_and_get_sent_payload()
        )

        for key in PORT_CONTROLS:
            # ignore fields we set or need to modify.  They are tested in subsequent test cases.
            if key not in [
                PortControlKey.DEV_ID,
                PortControlKey.MODE_SET_ID,
                PortControlKey.ON_SPEED,
                PortControlKey.DEV_ID,
                PortControlKey.MODE_SET_ID,
                PortControlKey.VPD_STATUS,
                PortControlKey.VPD_NUMS,
                PortControlKey.MASTER_PORT,
                PortControlKey.DEV_SETTING,
                PortControlKey.DEVICE_MAC_ADDR,
            ]:
                assert key in payload, f"Key {key} is missing"
                assert payload[key] == (
                    PORT_CONTROLS[key] or 0
                ), f"Key {key} has incorrect value"

    async def test_set_device_port_setting_value_changed_in_payload(self):
        """When setting a value, the value is updated in the built payload before sending"""
        payload = (
            await self.__make_generic_set_port_settings_call_and_get_sent_payload()
        )

        assert payload[PortControlKey.ON_SPEED] == 2

    @pytest.mark.parametrize("set_value", [0, None, 1])
    async def test_set_device_port_setting_zero_even_when_null(self, set_value):
        """When fetching existing settings before update, specified fields should be set to 0 if existing is null"""

        dev_mode_settings = GET_DEV_MODE_SETTING_LIST_PAYLOAD

        assert isinstance(dev_mode_settings["data"], dict)
        dev_mode_settings["data"][PortControlKey.SURPLUS] = set_value
        dev_mode_settings["data"][PortControlKey.TARGET_TEMPERATURE_SWITCH] = set_value
        dev_mode_settings["data"][PortControlKey.TARGET_HUMIDITY_SWITCH] = set_value
        dev_mode_settings["data"][PortControlKey.TARGET_VPD_SWITCH] = set_value
        dev_mode_settings["data"][PortControlKey.EC_OR_TDS] = set_value
        dev_mode_settings["data"][PortControlKey.MASTER_PORT] = set_value

        payload = await self.__make_generic_set_port_settings_call_and_get_sent_payload(
            dev_mode_settings
        )

        expected = set_value if set_value else 0
        assert payload[PortControlKey.SURPLUS] == expected
        assert payload[PortControlKey.TARGET_HUMIDITY_SWITCH] == expected
        assert payload[PortControlKey.TARGET_TEMPERATURE_SWITCH] == expected
        assert payload[PortControlKey.TARGET_VPD_SWITCH] == expected
        assert payload[PortControlKey.EC_OR_TDS] == expected
        assert payload[PortControlKey.MASTER_PORT] == expected

    async def test_set_device_port_setting_bad_fields_removed_and_missing_fields_added(
        self,
    ):
        """When setting a value, fields that are not passed to the update call when using the Android/iOS app should
        be stripped from the updated request payload. While devSettings exists, we also want to strip that as well
        as to not change controller settings unnecessarily."""

        payload = (
            await self.__make_generic_set_port_settings_call_and_get_sent_payload()
        )

        # bad fields removed
        assert PortControlKey.DEV_SETTING not in payload
        assert PortControlKey.IPC_SETTING not in payload
        assert PortControlKey.DEVICE_MAC_ADDR not in payload

        # missing fields added
        assert PortControlKey.VPD_STATUS in payload
        assert PortControlKey.VPD_NUMS in payload

    async def test_set_device_port_setting_dev_id_and_mode_set_id_are_int_values(self):
        """When setting a value, fields that are not passed to the update call when using the Android/iOS app should
        be stripped from the updated request payload. While devSettings exists, we also want to strip that as well
        as to not change controller settings unnecessarily."""

        payload = (
            await self.__make_generic_set_port_settings_call_and_get_sent_payload()
        )

        assert PortControlKey.DEV_ID in payload
        dev_id = payload[PortControlKey.DEV_ID]
        assert isinstance(dev_id, int)
        assert dev_id == DEVICE_ID

        assert PortControlKey.MODE_SET_ID in payload
        mode_set_id = payload[PortControlKey.MODE_SET_ID]
        assert isinstance(mode_set_id, int)
        assert mode_set_id == MODE_SET_ID

    @pytest.mark.parametrize("port", [0, 1, 2, 3, 4])
    async def test_get_device_settings_returns_settings(self, port: int):
        """When logged in, get controller settings should return the current settings"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID

        with aioresponses() as mocked:
            mocked.post(
                f"{HOST}{API_URL_GET_DEV_SETTING}",
                status=200,
                payload=GET_DEV_SETTINGS_PAYLOAD,
            )

            result = await client.get_device_settings(DEVICE_ID, port)

            assert result is not None
            assert result["devId"] == f"{DEVICE_ID}"

            gen = (request for request in mocked.requests.values())
            found = next(gen)

            assert found[0].kwargs["data"]["port"] == port

    async def test_get_device_settings_connect_error_on_not_logged_in(self):
        """When not logged in, get user devices should throw a connect error"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        with pytest.raises(ACInfinityClientCannotConnect):
            await client.get_device_settings(DEVICE_ID, 0)

    @staticmethod
    async def __make_generic_update_advanced_settings_call_and_get_sent_payload(
        dev_settings_payload=GET_DEV_SETTINGS_PAYLOAD,
    ):
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        with aioresponses() as mocked:
            mocked.post(
                f"{HOST}{API_URL_GET_DEV_SETTING}",
                status=200,
                payload=dev_settings_payload,
            )

            mocked.post(
                f"{HOST}{API_URL_UPDATE_ADV_SETTING}",
                status=200,
                payload=UPDATE_SUCCESS_PAYLOAD,
            )

            await client.update_advanced_settings(
                DEVICE_ID, 0, DEVICE_NAME, [(AdvancedSettingsKey.CALIBRATE_HUMIDITY, 3)]
            )

            gen = (request for request in mocked.requests.values())
            _ = next(gen)
            found = next(gen)
            return found[0].kwargs["data"]

    async def test_update_advanced_settings_copied_from_get_call(self):
        """When setting a value, first fetch the existing settings to build the payload"""

        payload = (
            await self.__make_generic_update_advanced_settings_call_and_get_sent_payload()
        )

        for key in DEVICE_SETTINGS:
            # ignore fields we set or need to modify.  They are tested in subsequent test cases.
            if key not in [
                AdvancedSettingsKey.SET_ID,
                AdvancedSettingsKey.DEV_MAC_ADDR,
                AdvancedSettingsKey.PORT_RESISTANCE,
                AdvancedSettingsKey.DEV_TIME_ZONE,
                AdvancedSettingsKey.SENSOR_SETTING,
                AdvancedSettingsKey.SENSOR_TRANS_BUFF,
                AdvancedSettingsKey.PORT_PARAM_DATA,
                AdvancedSettingsKey.SUB_DEVICE_VERSION,
                AdvancedSettingsKey.OTA_UPDATING,
                AdvancedSettingsKey.SEC_FUC_REPORT_TIME,
                AdvancedSettingsKey.UPDATE_ALL_PORT,
                AdvancedSettingsKey.CALIBRATION_TIME,
                AdvancedSettingsKey.DEV_ID,
                AdvancedSettingsKey.SUB_DEVICE_TYPE,
                AdvancedSettingsKey.SUPPORT_OTA,
                AdvancedSettingsKey.SUB_DEVICE_ID,
                AdvancedSettingsKey.SENSOR_TRANS_BUFF_STR,
                AdvancedSettingsKey.SENSOR_SETTING_STR,
                AdvancedSettingsKey.PORT_PARAM_DATA,
                AdvancedSettingsKey.DEV_NAME,
                AdvancedSettingsKey.CALIBRATE_HUMIDITY,
            ]:
                assert key in payload, f"Key {key} is missing"
                assert (
                    payload[key] == DEVICE_SETTINGS[key] or 0
                ), f"Key {key} has incorrect value"

    async def test_update_advanced_settings_value_changed_in_payload(self):
        """When setting a value, the value is updated in the built payload before sending"""

        payload = (
            await self.__make_generic_update_advanced_settings_call_and_get_sent_payload()
        )

        assert payload[AdvancedSettingsKey.CALIBRATE_HUMIDITY] == 3

    async def test_update_advanced_settings_bad_fields_removed_and_missing_fields_added(
        self,
    ):
        payload = (
            await self.__make_generic_update_advanced_settings_call_and_get_sent_payload()
        )

        # bad fields stripped before sending
        assert AdvancedSettingsKey.SET_ID not in payload
        assert AdvancedSettingsKey.DEV_MAC_ADDR not in payload
        assert AdvancedSettingsKey.PORT_RESISTANCE not in payload
        assert AdvancedSettingsKey.DEV_TIME_ZONE not in payload
        assert AdvancedSettingsKey.SENSOR_SETTING not in payload
        assert AdvancedSettingsKey.SENSOR_TRANS_BUFF not in payload
        assert AdvancedSettingsKey.SUB_DEVICE_VERSION not in payload
        assert AdvancedSettingsKey.SEC_FUC_REPORT_TIME not in payload
        assert AdvancedSettingsKey.UPDATE_ALL_PORT not in payload
        assert AdvancedSettingsKey.CALIBRATION_TIME not in payload

        # missing fields added before seending
        assert AdvancedSettingsKey.SENSOR_ONE_TYPE in payload
        assert AdvancedSettingsKey.IS_SHARE in payload
        assert AdvancedSettingsKey.TARGET_VPD_SWITCH in payload
        assert AdvancedSettingsKey.SENSOR_TWO_TYPE in payload
        assert AdvancedSettingsKey.PARAM_SENSORS in payload
        assert AdvancedSettingsKey.ZONE_SENSOR_TYPE in payload

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
        expected = set_value if set_value else 0
        assert payload[AdvancedSettingsKey.OTA_UPDATING] == expected
        assert payload[AdvancedSettingsKey.SUB_DEVICE_ID] == expected
        assert payload[AdvancedSettingsKey.SUB_DEVICE_TYPE] == expected
        assert payload[AdvancedSettingsKey.SUPPORT_OTA] == expected

    async def test_set_device_setting_dev_id_and_mode_set_id_are_int_values(self):
        """When setting a value, fields that are not passed to the update call when using the Android/iOS app should
        be stripped from the updated request payload. While devSettings exists, we also want to strip that as well
        as to not change controller settings unnecessarily."""

        payload = (
            await self.__make_generic_update_advanced_settings_call_and_get_sent_payload()
        )

        assert PortControlKey.DEV_ID in payload
        dev_id = payload[AdvancedSettingsKey.DEV_ID]
        assert isinstance(dev_id, int)
        assert dev_id == DEVICE_ID

    @pytest.mark.parametrize("set_value", ["", None, "{ 'key': 'value' }"])
    async def test_set_device_settings_null_str_fields_set_to_empty_string(
        self, set_value
    ):
        """When fetching existing settings before update, specified fields should be set to empty string if existing is null"""
        dev_settings = GET_DEV_SETTINGS_PAYLOAD

        assert isinstance(dev_settings["data"], dict)
        dev_settings["data"][AdvancedSettingsKey.PARAM_SENSORS] = set_value

        payload = await self.__make_generic_update_advanced_settings_call_and_get_sent_payload(
            dev_settings
        )

        expected = set_value if set_value else ""
        assert payload[AdvancedSettingsKey.PARAM_SENSORS] == expected
        assert payload[AdvancedSettingsKey.SENSOR_TRANS_BUFF_STR] == ""
        assert payload[AdvancedSettingsKey.SENSOR_SETTING_STR] == ""
        assert payload[AdvancedSettingsKey.PORT_PARAM_DATA] == ""

    async def test_set_device_settings_dev_name_pulled_from_existing_value(self):
        payload = (
            await self.__make_generic_update_advanced_settings_call_and_get_sent_payload()
        )

        assert AdvancedSettingsKey.DEV_NAME in payload
        assert payload[AdvancedSettingsKey.DEV_NAME] == DEVICE_NAME
