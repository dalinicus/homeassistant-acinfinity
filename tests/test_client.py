
import pytest
from aioresponses import aioresponses

from custom_components.ac_infinity.client import (
    API_URL_GET_DEVICE_INFO_LIST_ALL,
    API_URL_LOGIN,
    ACInfinityClient,
    ACInfinityClientCannotConnect,
    ACInfinityClientInvalidAuth,
)
from tests.data_models import (
    DEVICE_ID,
    DEVICE_INFO_LIST_ALL_PAYLOAD,
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

    @pytest.mark.parametrize("code", [500])
    async def test_login_api_auth_error_on_failed_login(self, code):
        """When login is called and returns a non-succesful status code, connect error should be raised"""

        with aioresponses() as mocked:
            mocked.post(
                f"{HOST}{API_URL_LOGIN}",
                status=200,
                payload={
                    "msg": "User Does Not Exist",
                    "code": code
                },
            )

            client = ACInfinityClient(HOST, EMAIL, PASSWORD)
            with pytest.raises(ACInfinityClientInvalidAuth):
                await client.login()

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
