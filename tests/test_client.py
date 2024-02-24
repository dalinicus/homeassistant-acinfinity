import pytest
from aioresponses import aioresponses

from custom_components.ac_infinity.client import (
    API_URL_ADD_DEV_MODE,
    API_URL_GET_DEV_MODE_SETTING,
    API_URL_GET_DEVICE_INFO_LIST_ALL,
    API_URL_LOGIN,
    ACInfinityClient,
    ACInfinityClientCannotConnect,
    ACInfinityClientInvalidAuth,
    ACInfinityClientRequestFailed,
)
from custom_components.ac_infinity.const import (
    SENSOR_SETTING_KEY_SURPLUS,
    SETTING_KEY_ON_SPEED,
)
from tests.data_models import (
    ADD_DEV_MODE_PAYLOAD,
    DEVICE_ID,
    DEVICE_INFO_LIST_ALL_PAYLOAD,
    DEVICE_SETTINGS_PAYLOAD,
    EMAIL,
    HOST,
    LOGIN_PAYLOAD,
    PASSWORD,
    USER_ID,
)


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
                await client.get_all_device_info()

    async def test_get_all_device_info_returns_user_devices(self):
        """When logged in, user devices should return a list of user devices"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID

        with aioresponses() as mocked:
            mocked.post(
                f"{HOST}{API_URL_GET_DEVICE_INFO_LIST_ALL}",
                status=200,
                payload=DEVICE_INFO_LIST_ALL_PAYLOAD,
            )

            result = await client.get_all_device_info()

            assert result is not None
            assert result[0]["devId"] == f"{DEVICE_ID}"

    async def test_get_all_device_info_connect_error_on_not_logged_in(self):
        """When not logged in, get user devices should throw a connect error"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        with pytest.raises(ACInfinityClientCannotConnect):
            await client.get_all_device_info()

    async def test_get_device_port_settings_connect_error_on_not_logged_in(self):
        """When not logged in, get user devices should throw a connect error"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        with pytest.raises(ACInfinityClientCannotConnect):
            await client.get_device_port_settings(DEVICE_ID, 1)

    async def test_set_device_port_setting_values_copied_from_get_call(self):
        """When setting a value, first fetch the existing settings to build the payload"""

        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        with aioresponses() as mocked:
            mocked.post(
                f"{HOST}{API_URL_GET_DEV_MODE_SETTING}",
                status=200,
                payload=DEVICE_SETTINGS_PAYLOAD,
            )

            mocked.post(
                f"{HOST}{API_URL_ADD_DEV_MODE}",
                status=200,
                payload=ADD_DEV_MODE_PAYLOAD,
            )

            await client.set_device_port_settings(
                DEVICE_ID, 4, [(SETTING_KEY_ON_SPEED, 2)]
            )

            gen = (request for request in mocked.requests.values())
            _ = next(gen)
            found = next(gen)
            payload = found[0].kwargs["data"]

            assert payload["acitveTimerOff"] == 0
            assert payload["acitveTimerOn"] == 0
            assert payload["activeCycleOff"] == 0
            assert payload["activeCycleOn"] == 0
            assert payload["activeHh"] == 0
            assert payload["activeHt"] == 1
            assert payload["activeHtVpd"] == 0
            assert payload["activeHtVpdNums"] == 99
            assert payload["activeLh"] == 0
            assert payload["activeLt"] == 0
            assert payload["activeLtVpd"] == 0
            assert payload["activeLtVpdNums"] == 1
            assert payload["atType"] == 2
            assert payload["devHh"] == 100
            assert payload["devHt"] == 89
            assert payload["devHtf"] == 193
            assert payload["devId"] == "1424979258063355749"
            assert payload["devLh"] == 0
            assert payload["devLt"] == 0
            assert payload["devLtf"] == 32
            assert payload["externalPort"] == 4
            assert payload["hTrend"] == 1
            assert payload["isOpenAutomation"] == 0
            assert payload["offSpead"] == 0
            assert payload["onlyUpdateSpeed"] == 0
            assert payload["schedEndtTime"] == 65535
            assert payload["schedStartTime"] == 65535
            assert payload["settingMode"] == 0
            assert payload["tTrend"] == 0
            assert payload["targetHumi"] == 0
            assert payload["targetHumiSwitch"] == 0
            assert payload["targetTSwitch"] == 0
            assert payload["targetTemp"] == 0
            assert payload["targetTempF"] == 32
            assert payload["targetVpd"] == 0
            assert payload["targetVpdSwitch"] == 0
            assert payload["trend"] == 0
            assert payload["unit"] == 0
            assert payload["vpdSettingMode"] == 0

    async def test_set_device_port_setting_value_changed_in_payload(self):
        """When setting a value, the value is updated in the built payload before sending"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        with aioresponses() as mocked:
            mocked.post(
                f"{HOST}{API_URL_GET_DEV_MODE_SETTING}",
                status=200,
                payload=DEVICE_SETTINGS_PAYLOAD,
            )

            mocked.post(
                f"{HOST}{API_URL_ADD_DEV_MODE}",
                status=200,
                payload=ADD_DEV_MODE_PAYLOAD,
            )

            await client.set_device_port_settings(
                DEVICE_ID, 4, [(SETTING_KEY_ON_SPEED, 2)]
            )

            gen = (request for request in mocked.requests.values())
            _ = next(gen)
            found = next(gen)
            payload = found[0].kwargs["data"]

            assert payload["onSpead"] == 2

    async def test_set_device_port_setting_surplus_zero_even_when_null(self):
        """When fetching existing settings before update, surplus should be set to 0 if existing is null"""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        with aioresponses() as mocked:
            mocked.post(
                f"{HOST}{API_URL_GET_DEV_MODE_SETTING}",
                status=200,
                payload=DEVICE_SETTINGS_PAYLOAD,
            )

            request_payload = ADD_DEV_MODE_PAYLOAD
            request_payload[SENSOR_SETTING_KEY_SURPLUS] = None

            mocked.post(
                f"{HOST}{API_URL_ADD_DEV_MODE}", status=200, payload=request_payload
            )

            await client.set_device_port_settings(
                DEVICE_ID, 4, [(SETTING_KEY_ON_SPEED, 2)]
            )

            gen = (request for request in mocked.requests.values())
            _ = next(gen)
            found = next(gen)
            payload = found[0].kwargs["data"]

            assert payload[SENSOR_SETTING_KEY_SURPLUS] == 0
