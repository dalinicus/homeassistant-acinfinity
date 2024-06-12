import asyncio
import logging
from abc import abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Awaitable, Callable, Tuple

import async_timeout
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from custom_components.ac_infinity.client import ACInfinityClient

from .const import DOMAIN, HOST, MANUFACTURER, ControllerPropertyKey, PortPropertyKey

_LOGGER = logging.getLogger(__name__)


class ACInfinityController:
    """
    A UIS enabled AC Infinity Controller
    """

    def __init__(self, controller_json: dict[str, Any]) -> None:
        """
        Args:
            controller_json: Json of an individual controller. This is typically obtained from
            /api/user/devInfoListAll endpoint, and would be a single object obtained from the array
            in the data field of the json returned.
        """

        self._device_id = str(controller_json[ControllerPropertyKey.DEVICE_ID])
        self._mac_addr = controller_json[ControllerPropertyKey.MAC_ADDR]
        self._device_name = controller_json[ControllerPropertyKey.DEVICE_NAME]
        self._identifier = (DOMAIN, self._device_id)
        self._ports = [
            ACInfinityPort(self, port)
            for port in controller_json[ControllerPropertyKey.DEVICE_INFO][
                ControllerPropertyKey.PORTS
            ]
        ]

        self._device_info = DeviceInfo(
            identifiers={self._identifier},
            name=self._device_name,
            manufacturer=MANUFACTURER,
            hw_version=controller_json[ControllerPropertyKey.HW_VERSION],
            sw_version=controller_json[ControllerPropertyKey.SW_VERSION],
            model=self.__get_device_model_by_device_type(
                controller_json[ControllerPropertyKey.DEVICE_TYPE]
            ),
        )

    @property
    def device_id(self) -> str:
        """The unique identifier of the UIS Controller"""
        return self._device_id

    @property
    def device_name(self) -> str:
        """The name of the controller as set in the Android/iOS app"""
        return self._device_name

    @property
    def mac_addr(self) -> str:
        """The unique mac address of the UIS controller's WI-FI network interface"""
        return self._mac_addr

    @property
    def ports(self) -> list["ACInfinityPort"]:
        """A list of USB-C ports associated with this controller and their associated settings, with or without a UIS child device plugged into it."""
        return self._ports

    @property
    def device_info(self) -> DeviceInfo:
        """A HAAS device definition visible in the device manager."""
        return self._device_info

    @property
    def identifier(self) -> tuple[str, str]:
        """The unique identifier for the HAAS device in the device manager."""
        return self._identifier

    @staticmethod
    def __get_device_model_by_device_type(device_type: int) -> str:
        match device_type:
            case 11:
                return "UIS Controller 69 Pro (CTR69P)"
            case _:
                return f"UIS Controller Type {device_type}"


class ACInfinityPort:
    """
    A USB-C port associated with this controller and its associated settings,
    with or without a UIS child device (fan, light, etc...) plugged into it.
    """

    def __init__(
        self, controller: ACInfinityController, port_json: dict[str, Any]
    ) -> None:
        """
        Args:
            controller: The controller that the USB-C port is attached to
            port_json: Json of an individual controller. This is typically obtained from
            the ports field of a single controller returned from the /api/user/devInfoListAll endpoint.
            See the ports property on ACInfinityController.
        """

        self._controller = controller
        self._port_index = port_json[PortPropertyKey.PORT]
        self._port_name = port_json[PortPropertyKey.NAME]
        self._identifier = (DOMAIN, f"{controller.device_id}_{self._port_index}")

        self._device_info = DeviceInfo(
            identifiers={self._identifier},
            name=f"{controller.device_name} {self.port_name}",
            manufacturer=MANUFACTURER,
            via_device=controller.identifier,
            model="UIS Enabled Device",
        )

    @property
    def controller(self) -> ACInfinityController:
        """The parent controller for this USB-C port"""
        return self._controller

    @property
    def port_index(self) -> int:
        """The index of the USB-C port, as labeled on the controller"""
        return self._port_index

    @property
    def port_name(self) -> str:
        """The name of the USB-C port, as set by the user in the Android/iOS app"""
        return self._port_name

    @property
    def device_info(self) -> DeviceInfo:
        """A HAAS device definition visible in the device manager. Will be a child to the device associated with the parent controller."""
        return self._device_info


class ACInfinityService:
    """Service layer object responsible for initializing and updating values from the AC Infinity API"""

    MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)

    # api/user/devInfoListAll json organized by controller device id
    _controller_properties: dict[str, Any] = {}

    # api/user/devInfoListAll json organized by controller device id and port index
    _port_properties: dict[Tuple[str, int], Any] = {}

    # api/dev/getDevSetting json organized by controller device id
    _controller_settings: dict[str, Any] = {}

    # api/dev/getDevModeSettingList json organized by controller device id and port index
    _port_settings: dict[Tuple[str, int], Any] = {}

    def __init__(self, email: str, password: str) -> None:
        """
        Args:
            email: email address to use to log into the AC Infinity API.  Set by user via config_flow during integration setup
            password: password to use to log into the AC Infinity API.  Set by the user via config_flow during integration setup
        """
        self._client = ACInfinityClient(HOST, email, password)

    def get_controller_property(
        self, controller_id: (str | int), property_key: str, default_value=None
    ):
        """gets a property value for a given controller, if both the property and controller exist.

        Args:
            controller_id: the device id of the controller
            property_key: the json field name for the data being retrieved
            default_value: the value to return if the controller or property doesn't exist
        """
        normalized_id = str(controller_id)
        if normalized_id in self._controller_properties:
            result = self._controller_properties[normalized_id]
            if property_key in result:
                return result[property_key]
            elif property_key in result[ControllerPropertyKey.DEVICE_INFO]:
                value = result[ControllerPropertyKey.DEVICE_INFO][property_key]
                return value if value is not None else default_value

        return default_value

    def __set_controller_properties_json(
        self, controller_id: (str | int), json: Any
    ) -> None:
        """sets the json properties data for a given controller

        Args:
            controller_id: the device id of the controller
            json: the relevant json snippet from the returned API payload
        """
        self._controller_properties[str(controller_id)] = json

    def get_port_property(
        self,
        controller_id: (str | int),
        port_index: int,
        property_key: str,
        default_value=None,
    ):
        """gets a property value for a given port on a controller, if the property, controller and port all exist.

        Args:
            controller_id:  the device id of the controller
            port_index: the index of the port on the controller
            property_key: the json filed name for the data being retrieved
            default_value: the default value to return if the controller, port, or property doesn't exist
        """
        normalized_id = (str(controller_id), port_index)
        if normalized_id in self._port_properties:
            found = self._port_properties[normalized_id]
            if property_key in found:
                value = found[property_key]
                return value if value is not None else default_value

        return default_value

    def __set_port_properties_json(
        self, controller_id: str, port_index: int, json: Any
    ) -> None:
        """sets the json properties data for a given controller and port

        Args:
            controller_id: the device id of the controller
            port_index: the index of the port on the controller
            json: the relevant json snippet from the returned API payload
        """
        self._port_properties[(controller_id, port_index)] = json

    def get_controller_setting(
        self, controller_id: (str | int), setting_key: str, default_value=None
    ):
        """gets a property value for a given controller, if both the property and controller exist.

        Args:
            controller_id: the device id of the controller
            setting_key: the json field name for the data being retrieved
            default_value: the value to return if the controller or property doesn't exist
        """
        normalized_id = str(controller_id)
        if normalized_id in self._controller_settings:
            result = self._controller_settings[normalized_id]
            if setting_key in result:
                value = result[setting_key]
                return value if value is not None else default_value

        return default_value

    def __set_controller_settings_json(self, controller_id: str, json: Any) -> None:
        """sets the json settings data for a given controller

        Args:
            controller_id: the device id of the controller
            json: he relevant json snippet from the returned API payload
        """
        self._controller_settings[controller_id] = json

    def get_port_setting(
        self,
        controller_id: (str | int),
        port_index: int,
        setting_key: str,
        default_value=None,
    ):
        """gets the current set value for a given device setting

        Args:
            controller_id: the device id of the controller
            port_index: the index of the port on the controller
            setting_key: the setting to pull the value of
            default_value: the default value to return if the controller, port, or setting doesn't exist
        """
        normalized_id = (str(controller_id), port_index)
        if normalized_id in self._port_settings:
            found = self._port_settings[normalized_id]
            if setting_key in found:
                value = found[setting_key]
                return value if value is not None else default_value

        return default_value

    def __set_port_settings_json(
        self, controller_id: str, port_index: int, json: Any
    ) -> None:
        """sets the json setting data for a given controller and port

        Args:
            controller_id: the device id of the controller
            port_index: the index of the port on the controller
            json: the relevant json snippet from the returned API payload
        """
        self._port_settings[(controller_id, port_index)] = json

    async def refresh(self) -> None:
        """refreshes the values of properties and settings from the AC infinity API"""
        try_count = 0
        while True:
            try:
                if not self._client.is_logged_in():
                    await self._client.login()

                all_devices_json = await self._client.get_devices_list_all()
                for controller_properties_json in all_devices_json:
                    controller_id = controller_properties_json[
                        ControllerPropertyKey.DEVICE_ID
                    ]

                    # set controller properties; readings for temp, vpd, humidity, etc...
                    self.__set_controller_properties_json(
                        controller_id, controller_properties_json
                    )

                    # retrieve and set controller settings; temperature, humidity, and vpd offsets
                    controller_settings_json = await self._client.get_device_settings(
                        controller_id
                    )
                    self.__set_controller_settings_json(
                        controller_id, controller_settings_json
                    )

                    for port_properties_json in controller_properties_json[
                        ControllerPropertyKey.DEVICE_INFO
                    ][ControllerPropertyKey.PORTS]:
                        port_index = port_properties_json[PortPropertyKey.PORT]

                        # set port properties; current power and remaining time until a mode switch
                        self.__set_port_properties_json(
                            controller_id, port_index, port_properties_json
                        )

                        # retrieve and set port settings; current mode, temperature triggers, on/off speed, etc...
                        port_settings_json = (
                            await self._client.get_device_mode_settings_list(
                                controller_id, port_index
                            )
                        )
                        self.__set_port_settings_json(
                            controller_id, port_index, port_settings_json
                        )
                return  # update successful.  eject from the infinite while loop.
            except BaseException as ex:
                if try_count < 2:
                    try_count += 1
                    _LOGGER.warning(
                        "Unable to refresh from data update coordinator. Retry attempt %s/2",
                        str(try_count),
                    )
                    await asyncio.sleep(1)
                else:
                    _LOGGER.error(
                        "Unable to refresh from data update coordinator. Retry attempt limit exceeded",
                        exc_info=ex,
                    )
                    raise

    def get_all_controller_properties(self) -> list[ACInfinityController]:
        """gets device metadata, such as ids, labels, macaddr, etc... that are not expected to change"""
        if self._controller_properties is None:
            return []

        return [
            ACInfinityController(device)
            for device in self._controller_properties.values()
        ]

    async def update_controller_setting(
        self,
        controller_id: (str | int),
        setting_key: str,
        new_value: int,
    ):
        """Update the value of a setting via the AC Infinity API

        Args:
            controller_id: the device id of the controller
            setting_key: the setting to update the value of
            new_value: the new value of the setting to set
        """
        await self.update_controller_settings(controller_id, [(setting_key, new_value)])

    async def update_controller_settings(
        self,
        controller_id: (str | int),
        key_values: list[Tuple[str, int]],
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller_id: the device id of the controller
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        try_count = 0
        while True:
            try:
                device_name = self.get_controller_property(
                    controller_id, ControllerPropertyKey.DEVICE_NAME
                )
                await self._client.update_device_settings(
                    controller_id, device_name, key_values
                )
                return
            except BaseException as ex:
                if try_count < 2:
                    try_count += 1
                    _LOGGER.warning(
                        "Unable to update controller settings. Retry attempt %s/2",
                        str(try_count),
                    )
                    await asyncio.sleep(1)
                else:
                    _LOGGER.error(
                        "Unable to update controller settings. Retry attempt limit exceeded",
                        exc_info=ex,
                    )
                    raise

    async def update_port_setting(
        self,
        controller_id: (str | int),
        port_index: int,
        setting_key: str,
        new_value: int,
    ):
        """Update the value of a setting via the AC Infinity API

        Args:
            controller_id: the device id of the controller
            port_index: the index of the port on the controller
            setting_key: the setting to update the value of
            new_value: the new value of the setting to set
        """
        await self.update_port_settings(
            controller_id, port_index, [(setting_key, new_value)]
        )

    async def update_port_settings(
        self,
        controller_id: (str | int),
        port_index: int,
        key_values: list[tuple[str, int]],
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller_id: the device id of the controller
            port_index: the index of the port on the controller
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        try_count = 0
        while True:
            try:
                await self._client.set_device_mode_settings(
                    controller_id, port_index, key_values
                )
                return
            except BaseException as ex:
                if try_count < 2:
                    try_count += 1
                    _LOGGER.warning(
                        "Unable to update settings. Retry attempt %s/2", str(try_count)
                    )
                    await asyncio.sleep(1)
                else:
                    _LOGGER.error(
                        "Unable to update settings. Retry attempt limit exceeded",
                        exc_info=ex,
                    )
                    raise


class ACInfinityDataUpdateCoordinator(DataUpdateCoordinator):
    """Handles updating data for the integration"""

    def __init__(self, hass, service: ACInfinityService, polling_interval: int):
        """Constructor"""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=polling_interval),
        )

        self._ac_infinity = service

    async def _async_update_data(self):
        """Fetch data from the AC Infinity API"""
        _LOGGER.debug("Refreshing data from data update coordinator")
        try:
            async with async_timeout.timeout(10):
                await self._ac_infinity.refresh()
                return self._ac_infinity
        except Exception as e:
            _LOGGER.error("Unable to refresh from data update coordinator", exc_info=e)
            raise UpdateFailed from e

    @property
    def ac_infinity(self) -> ACInfinityService:
        return self._ac_infinity


class ACInfinityEntity(CoordinatorEntity[ACInfinityDataUpdateCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        data_key: str,
    ):
        super().__init__(coordinator)
        self._data_key = data_key

    @property
    def ac_infinity(self) -> ACInfinityService:
        """Returns the underlying ac_infinity api object from the assigned coordinator"""
        return self.coordinator.ac_infinity

    @property
    @abstractmethod
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""

    @property
    @abstractmethod
    def device_info(self) -> DeviceInfo:
        """Returns the device info for the controller entity"""


class ACInfinityControllerEntity(ACInfinityEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        controller: ACInfinityController,
        data_key: str,
    ):
        super().__init__(coordinator, data_key)
        self._controller = controller

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""
        return f"{DOMAIN}_{self._controller.mac_addr}_{self._data_key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Returns the device info for the controller entity"""
        return self._controller.device_info

    @property
    def controller(self) -> ACInfinityController:
        return self._controller


class ACInfinityPortEntity(ACInfinityEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        port: ACInfinityPort,
        data_key: str,
    ):
        super().__init__(coordinator, data_key)
        self._port = port

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""
        return f"{DOMAIN}_{self._port.controller.mac_addr}_port_{self._port.port_index}_{self._data_key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Returns the device info for the port entity"""
        return self._port.device_info

    @property
    def port(self) -> ACInfinityPort:
        return self._port


@dataclass
class ACInfinityControllerReadOnlyMixin:
    """Mixin for retrieving values for controller level sensors"""

    get_value_fn: Callable[[ACInfinityEntity, ACInfinityController], StateType]
    """Input data object and a device id; output the value."""


@dataclass
class ACInfinityControllerReadWriteMixin(ACInfinityControllerReadOnlyMixin):
    """Mixin for retrieving and updating values for controller level settings"""

    set_value_fn: Callable[
        [ACInfinityEntity, ACInfinityController, StateType], Awaitable[None]
    ]
    """Input data object, device id, port number, and desired value."""


@dataclass
class ACInfinityPortReadOnlyMixin:
    """Mixin for retrieving values for port device level sensors"""

    get_value_fn: Callable[[ACInfinityEntity, ACInfinityPort], StateType]
    """Input data object, device id, and port number; output the value."""


@dataclass
class ACInfinityPortReadWriteMixin(ACInfinityPortReadOnlyMixin):
    """Mixin for retrieving and updating values for port device level settings"""

    set_value_fn: Callable[
        [ACInfinityEntity, ACInfinityPort, StateType], Awaitable[None]
    ]
    """Input data object, device id, port number, and desired value."""


def get_value_fn_port_property_default(entity: ACInfinityEntity, port: ACInfinityPort):
    return entity.ac_infinity.get_port_property(
        port.controller.device_id, port.port_index, entity.entity_description.key
    )


def get_value_fn_controller_setting_default(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return entity.ac_infinity.get_controller_setting(
        controller.device_id, entity.entity_description.key
    )


def set_value_fn_controller_setting_default(
    entity: ACInfinityEntity, controller: ACInfinityController, value: int
):
    return entity.ac_infinity.update_controller_setting(
        controller.device_id, entity.entity_description.key, value
    )


def get_value_fn_port_setting_default(entity: ACInfinityEntity, port: ACInfinityPort):
    return entity.ac_infinity.get_port_setting(
        port.controller.device_id, port.port_index, entity.entity_description.key
    )


def set_value_fn_port_setting_default(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    return entity.ac_infinity.update_port_setting(
        port.controller.device_id, port.port_index, entity.entity_description.key, value
    )
