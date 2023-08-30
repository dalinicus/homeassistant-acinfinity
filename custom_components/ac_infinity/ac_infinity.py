from datetime import timedelta
from typing import List

from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import Throttle

from .client import ACInfinityClient
from .const import (
    DEVICE_KEY_DEVICE_ID,
    DEVICE_KEY_DEVICE_INFO,
    DEVICE_KEY_DEVICE_NAME,
    DEVICE_KEY_MAC_ADDR,
    DEVICE_KEY_PORTS,
    DEVICE_PORT_KEY_NAME,
    DEVICE_PORT_KEY_PORT,
    HOST,
)


class ACInfinityDevice:
    def __init__(self, device_json) -> None:
        self._device_id = str(device_json[DEVICE_KEY_DEVICE_ID])
        self._mac_addr = device_json[DEVICE_KEY_MAC_ADDR]
        self._device_name = device_json[DEVICE_KEY_DEVICE_NAME]
        self._ports = [
            ACInfinityDevicePort(port) for port in device_json[DEVICE_KEY_DEVICE_INFO][DEVICE_KEY_PORTS]
        ]

    @property
    def device_id(self):
        return self._device_id

    @property
    def device_name(self):
        return self._device_id

    @property
    def mac_addr(self):
        return self._mac_addr

    @property
    def ports(self):
        return self._ports

class ACInfinityDevicePort:
    def __init__(self, device_json) -> None:
        self._port_id = device_json[DEVICE_PORT_KEY_PORT]
        self._port_name = device_json[DEVICE_PORT_KEY_NAME]

    @property
    def port_id(self):
        return self._port_id

    @property
    def port_name(self):
        return self._port_name

class ACInfinity:
    MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)

    def __init__(self, email: str, password: str) -> None:
        self._client = ACInfinityClient(HOST, email, password)
        self._data: dict = {}

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def update(self):
        try:
            if not self._client.is_logged_in():
                await self._client.login()

            self._data = await self._client.get_all_device_info()
        except Exception:
            raise UpdateFailed from Exception

    def get_all_device_meta_data(self) -> List[ACInfinityDevice]:
        """gets device metadata, such as ids, labels, macaddr, etc.. that are not expected to change"""
        if(self._data) is None:
            return []

        return (
            [ ACInfinityDevice(device) for device in self._data]
        )

    def get_device_property(self, device_id:(str|int), property:str):
        """ gets a property, if it exists, from a given device, if it exists"""
        result = next((
            device for device in self._data
            if device[DEVICE_KEY_DEVICE_ID] == str(device_id)
        ), None)

        if result is not None:
            if property in result:
                return result[property]
            elif property in result[DEVICE_KEY_DEVICE_INFO]:
                return result[DEVICE_KEY_DEVICE_INFO][property]

        return None

    def get_device_port_property(self, device_id:str, port_id:int, property:str):
        """ gets a property, if it exists, from the given port, if it exists,  from the given device, if it exists"""
        result = next((
            port for device in self._data
            if device[DEVICE_KEY_DEVICE_ID] == str(device_id)
            for port in device[DEVICE_KEY_DEVICE_INFO][DEVICE_KEY_PORTS]
            if port[DEVICE_PORT_KEY_PORT] == port_id
        ), None)

        if result is not None and property in result:
            return result[property]

        return None
