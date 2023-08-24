import aiohttp
import async_timeout
from homeassistant.exceptions import HomeAssistantError

HOST = "http://www.acinfinityserver.com"

API_URL_LOGIN = "/api/user/appUserLogin"
API_URL_GET_DEVICE_INFO_LIST_ALL = "/api/user/devInfoListAll"


class ACInfinityClient:
    def __init__(self, email: str, password: str) -> None:
        self._email = email
        self._password = password

        self._user_id: (str | None) = None

    async def login(self):
        headers = self.__create_headers(use_auth_token=False)
        response = await self.__post(
            API_URL_LOGIN,
            {"appEmail": self._email, "appPasswordl": self._password},
            headers,
        )
        self._user_id = response["data"]["appId"]

    def is_logged_in(self):
        return True if self._user_id else False

    async def get_all_device_info(self):
        if not self.is_logged_in():
            raise ACInfinityClientCannotConnect("Aerogarden client is not logged in.")

        headers = self.__create_headers(use_auth_token=True)
        json = await self.__post(
            API_URL_GET_DEVICE_INFO_LIST_ALL, {"userId": self._user_id}, headers
        )
        return json["data"]

    async def __post(self, path, post_data, headers):
        async with async_timeout.timeout(10), aiohttp.ClientSession(
            raise_for_status=False, headers=headers
        ) as session, session.post(f"{HOST}/{path}", data=post_data) as response:
            if response.status != 200:
                raise ACInfinityClientCannotConnect

            json = await response.json()
            if json["code"] != 200:
                raise ACInfinityClientInvalidAuth

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
