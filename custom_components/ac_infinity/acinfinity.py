from datetime import timedelta

import aiohttp
import async_timeout
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import Throttle

from .const import (
    DEVICE_LABEL,
    DEVICE_MAC_ADDR,
    DEVICE_PORT_INDEX,
    DEVICE_PORT_LABEL,
    DEVICE_PORTS,
    SENSOR_KEY_HUMIDITY,
    SENSOR_KEY_TEMPERATURE,
    SENSOR_KEY_VPD,
    SENSOR_PORT_KEY_INTENSITY,
    SENSOR_PORT_KEY_ONLINE,
)
from .helpers import assemble_port_sensor_key


class ACInfinity:
    MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)

    def __init__(self, userId) -> None:
        self._client = ACInfinityClient(userId)
        self._data: dict = {}

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def update_data(self):
        try:
            devices = {}
            for device in await self._client.get_all_device_info():
                macAddr = device["devMacAddr"]

                deviceObj = {
                    SENSOR_KEY_TEMPERATURE: device["deviceInfo"]["temperature"] / 100,
                    SENSOR_KEY_HUMIDITY: device["deviceInfo"]["humidity"] / 100,
                    SENSOR_KEY_VPD: device["deviceInfo"]["vpdnums"] / 100,
                }

                for portDevice in device["deviceInfo"]["ports"]:
                    portNum = portDevice["port"]
                    deviceObj[
                        assemble_port_sensor_key(portNum, SENSOR_PORT_KEY_ONLINE)
                    ] = portDevice["online"]
                    deviceObj[
                        assemble_port_sensor_key(portNum, SENSOR_PORT_KEY_INTENSITY)
                    ] = portDevice["speak"]

                devices[macAddr] = deviceObj
            self._data = devices
        except Exception:
            raise UpdateFailed from Exception

    async def get_registered_devices(self):
        devices = []
        for device in await self._client.get_all_device_info():
            deviceObj = {
                DEVICE_MAC_ADDR: device["devMacAddr"],
                DEVICE_LABEL: device["devName"],
            }

            ports = []
            for portDevice in device["deviceInfo"]["ports"]:
                ports.append(
                    {
                        DEVICE_PORT_INDEX: portDevice["port"],
                        DEVICE_PORT_LABEL: portDevice["portName"],
                    }
                )
            deviceObj[DEVICE_PORTS] = ports
            devices.append(deviceObj)
        return devices

    def get_sensor_data(self, macAddr: str, sensorKey: str):
        if macAddr in self._data:
            return self._data[macAddr][sensorKey]
        return None


class ACInfinityClient:
    HOST = "http://www.acinfinityserver.com"
    GET_DEVICE_INFO_LIST_ALL = "/api/user/devInfoListAll"

    def __init__(self, userId) -> None:
        self._userId = userId
        self._headers = {
            "User-Agent": "ACController/1.8.2 (com.acinfinity.humiture; build:489; iOS 16.5.1) Alamofire/5.4.4",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "token": userId,
        }

    async def get_all_device_info(self):
        json = await self.__post(
            self.GET_DEVICE_INFO_LIST_ALL, f"userId={self._userId}"
        )
        return json["data"]

    async def __post(self, path, post_data):
        async with async_timeout.timeout(10), aiohttp.ClientSession(
            raise_for_status=False, headers=self._headers
        ) as session, session.post(f"{self.HOST}/{path}", data=post_data) as response:
            if response.status != 200:
                raise CannotConnect

            json = await response.json()
            if json["code"] != 200:
                raise InvalidAuth

            return json


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
