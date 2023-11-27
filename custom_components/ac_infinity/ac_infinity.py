import asyncio
import logging
from datetime import timedelta
from typing import Any, Tuple

from homeassistant.helpers.entity import DeviceInfo

from .client import ACInfinityClient
from .const import (
    DOMAIN,
    HOST,
    MANUFACTURER,
    PROPERTY_KEY_DEVICE_ID,
    PROPERTY_KEY_DEVICE_INFO,
    PROPERTY_KEY_DEVICE_NAME,
    PROPERTY_KEY_DEVICE_TYPE,
    PROPERTY_KEY_HW_VERSION,
    PROPERTY_KEY_MAC_ADDR,
    PROPERTY_KEY_PORTS,
    PROPERTY_KEY_SW_VERSION,
    PROPERTY_PORT_KEY_NAME,
    PROPERTY_PORT_KEY_PORT,
)

_LOGGER = logging.getLogger(__name__)


class ACInfinityController:
    def __init__(self, device_json) -> None:
        # device info
        self._device_id = str(device_json[PROPERTY_KEY_DEVICE_ID])
        self._mac_addr = device_json[PROPERTY_KEY_MAC_ADDR]
        self._device_name = device_json[PROPERTY_KEY_DEVICE_NAME]
        self._identifier = (DOMAIN, self._device_id)
        self._ports = [
            ACInfinityPort(self, port)
            for port in device_json[PROPERTY_KEY_DEVICE_INFO][PROPERTY_KEY_PORTS]
        ]

        self._device_info = DeviceInfo(
            identifiers={self._identifier},
            name=self._device_name,
            manufacturer=MANUFACTURER,
            hw_version=device_json[PROPERTY_KEY_HW_VERSION],
            sw_version=device_json[PROPERTY_KEY_SW_VERSION],
            model=self.__get_device_model_by_device_type(
                device_json[PROPERTY_KEY_DEVICE_TYPE]
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

    @property
    def identifier(self):
        return self._identifier

    def __get_device_model_by_device_type(self, device_type: int):
        match device_type:
            case 11:
                return "UIS Controller 69 Pro (CTR69P)"
            case _:
                return f"UIS Controller Type {device_type}"


class ACInfinityPort:
    def __init__(self, controller: ACInfinityController, device_port_json) -> None:
        self._controller = controller
        self._port_id = device_port_json[PROPERTY_PORT_KEY_PORT]
        self._port_name = device_port_json[PROPERTY_PORT_KEY_NAME]

        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{controller._device_id}_{self._port_id}")},
            name=f"{controller.device_name} {self.port_name}",
            manufacturer=MANUFACTURER,
            via_device=controller.identifier,
            model="UIS Enabled Device",
        )

    @property
    def parent_device_id(self):
        return self._controller.device_id

    @property
    def parent_mac_addr(self):
        return self._controller.mac_addr

    @property
    def port_id(self):
        return self._port_id

    @property
    def port_name(self):
        return self._port_name

    @property
    def device_info(self):
        return self._device_info


class ACInfinity:
    MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)

    def __init__(self, email: str, password: str) -> None:
        self._client = ACInfinityClient(HOST, email, password)
        self._devices: dict[str, dict[str, Any]] = {}
        self._port_settings: dict[str, dict[int, Any]] = {}

    async def update(self):
        """refreshes the values of properties and settings from the AC infinity API"""
        tryCount = 0
        while True:
            try:
                if not self._client.is_logged_in():
                    await self._client.login()

                device_list = await self._client.get_all_device_info()
                for device in device_list:
                    device_id = device[PROPERTY_KEY_DEVICE_ID]
                    self._devices[device_id] = device
                    self._port_settings[device_id] = {}
                    for port in device[PROPERTY_KEY_DEVICE_INFO][PROPERTY_KEY_PORTS]:
                        port_id = port[PROPERTY_PORT_KEY_PORT]
                        self._port_settings[device_id][
                            port_id
                        ] = await self._client.get_device_port_settings(
                            device_id, port_id
                        )
                return
            except BaseException as ex:
                if tryCount < 2:
                    tryCount += 1
                    _LOGGER.warning(
                        "Unable to refresh from data update coordinator. Retry attempt %s/2",
                        str(tryCount),
                    )
                    await asyncio.sleep(1)
                else:
                    _LOGGER.error(
                        "Unable to refresh from data update coordinator. Retry attempt limit exceeded",
                        exc_info=ex,
                    )
                    raise

    def get_all_device_meta_data(self) -> list[ACInfinityController]:
        """gets device metadata, such as ids, labels, macaddr, etc.. that are not expected to change"""
        if (self._devices) is None:
            return []

        return [ACInfinityController(device) for device in self._devices.values()]

    def get_device_property(self, device_id: (str | int), property_key: str):
        """gets a property of a controller, if it exists, from a given device, if it exists"""
        if str(device_id) in self._devices:
            result = self._devices[str(device_id)]
            if property_key in result:
                return result[property_key]
            elif property_key in result[PROPERTY_KEY_DEVICE_INFO]:
                return result[PROPERTY_KEY_DEVICE_INFO][property_key]

        return None

    def get_device_port_property(
        self, device_id: (str | int), port_id: int, property_key: str
    ):
        """gets a property, if it exists, from the given port, if it exists, from a child of the given controller device, if it exists

        Properties are read-only values reported from the parent controller via devInfoListAll, as opposed to settings with are read/write
        values reported from getdevModeSettingList for the individual port device
        """
        if str(device_id) in self._devices:
            device = self._devices[str(device_id)]
            result = next(
                (
                    port
                    for port in device[PROPERTY_KEY_DEVICE_INFO][PROPERTY_KEY_PORTS]
                    if port[PROPERTY_PORT_KEY_PORT] == port_id
                ),
                None,
            )

            if result is not None and property_key in result:
                return result[property_key]

        return None

    def get_device_port_setting(
        self, device_id: (str | int), port_id: int, setting: str, default_value=None
    ):
        """gets the current set value for a given device setting

        Settings are read/write values reported from getdevModeSettinList for an individual port device, as opposed to
        port properties, which are read-only values reported by the parent controller via devInfoListAll
        """
        device_id_str = str(device_id)
        if (
            device_id_str in self._port_settings
            and port_id in self._port_settings[device_id_str]
            and setting in self._port_settings[device_id_str][port_id]
        ):
            value = self._port_settings[device_id_str][port_id][setting]
            if value is not None:
                return value

        return default_value

    async def set_device_port_setting(
        self, device_id: (str | int), port_id: int, setting: str, value: int
    ):
        """set a desired value for a given device setting"""
        await self.set_device_port_settings(device_id, port_id, [(setting, value)])

    async def set_device_port_settings(
        self, device_id: (str | int), port_id: int, keyValues: list[Tuple[str, int]]
    ):
        """set a desired value for a given device setting"""
        tryCount = 0
        while True:
            try:
                await self._client.set_device_port_settings(
                    device_id, port_id, keyValues
                )
                return
            except BaseException as ex:
                if tryCount < 2:
                    tryCount += 1
                    _LOGGER.warning(
                        "Unable to update settings. Retry attempt %s/2", str(tryCount)
                    )
                    await asyncio.sleep(1)
                else:
                    _LOGGER.error(
                        "Unable to update settings. Retry attempt limit exceeded",
                        exc_info=ex,
                    )
                    raise
