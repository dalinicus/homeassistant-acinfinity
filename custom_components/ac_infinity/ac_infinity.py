from datetime import timedelta
from typing import Any, List

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import Throttle

from .client import ACInfinityClient
from .const import (
    DEVICE_KEY_DEVICE_ID,
    DEVICE_KEY_DEVICE_INFO,
    DEVICE_KEY_DEVICE_NAME,
    DEVICE_KEY_DEVICE_TYPE,
    DEVICE_KEY_HW_VERSION,
    DEVICE_KEY_MAC_ADDR,
    DEVICE_KEY_PORTS,
    DEVICE_KEY_SW_VERSION,
    DEVICE_PORT_KEY_NAME,
    DEVICE_PORT_KEY_PORT,
    DOMAIN,
    HOST,
    MANUFACTURER,
)


class ACInfinityDevice:
    def __init__(self, device_json) -> None:
        # device info
        self._device_id = str(device_json[DEVICE_KEY_DEVICE_ID])
        self._mac_addr = device_json[DEVICE_KEY_MAC_ADDR]
        self._device_name = device_json[DEVICE_KEY_DEVICE_NAME]

        self._ports = [
            ACInfinityDevicePort(port)
            for port in device_json[DEVICE_KEY_DEVICE_INFO][DEVICE_KEY_PORTS]
        ]

        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
            manufacturer=MANUFACTURER,
            hw_version=device_json[DEVICE_KEY_HW_VERSION],
            sw_version=device_json[DEVICE_KEY_SW_VERSION],
            model=self.__get_device_model_by_device_type(
                device_json[DEVICE_KEY_DEVICE_TYPE]
            ),
        )

    @property
    def device_id(self):
        return self._device_id

    @property
    def device_name(self):
        return self._device_name

    @property
    def mac_addr(self):
        return self._mac_addr

    @property
    def ports(self):
        return self._ports

    @property
    def device_info(self):
        return self._device_info

    def __get_device_model_by_device_type(self, device_type: int):
        match device_type:
            case 11:
                return "Controller 69 Pro (CTR69P)"
            case _:
                return f"Controller Type {device_type}"


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
        self._data: list[dict[str, Any]] = []

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
        if (self._data) is None:
            return []

        return [ACInfinityDevice(device) for device in self._data]

    def get_device_property(self, device_id: (str | int), property: str):
        """gets a property, if it exists, from a given device, if it exists"""
        result = next(
            (
                device
                for device in self._data
                if device[DEVICE_KEY_DEVICE_ID] == str(device_id)
            ),
            None,
        )

        if result is not None:
            if property in result:
                return result[property]
            elif property in result[DEVICE_KEY_DEVICE_INFO]:
                return result[DEVICE_KEY_DEVICE_INFO][property]

        return None

    def get_device_port_property(
        self, device_id: (str | int), port_id: int, property: str
    ):
        """gets a property, if it exists, from the given port, if it exists,  from the given device, if it exists"""
        result = next(
            (
                port
                for device in self._data
                if device[DEVICE_KEY_DEVICE_ID] == str(device_id)
                for port in device[DEVICE_KEY_DEVICE_INFO][DEVICE_KEY_PORTS]
                if port[DEVICE_PORT_KEY_PORT] == port_id
            ),
            None,
        )

        if result is not None and property in result:
            return result[property]

        return None
