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

from .const import (
    DOMAIN,
    HOST,
    MANUFACTURER,
    ControllerPropertyKey,
    ControllerType,
    PortControlKey,
    PortPropertyKey,
    SensorPropertyKey,
    SensorType,
)

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
        self._device_type = controller_json[ControllerPropertyKey.DEVICE_TYPE]
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

        # controller AI will have a sensor array.
        self._sensors = (
            [
                ACInfinitySensor(self, sensor)
                for sensor in controller_json[ControllerPropertyKey.DEVICE_INFO][
                    ControllerPropertyKey.SENSORS
                ]
            ]
            if ControllerPropertyKey.SENSORS
            in controller_json[ControllerPropertyKey.DEVICE_INFO]
            and controller_json[ControllerPropertyKey.DEVICE_INFO][
                ControllerPropertyKey.SENSORS
            ]
            is not None
            else []
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
    def device_type(self) -> str:
        """The integer id of the device type of this controller (Pro, Pro+, AI+, etc...)"""
        return self._device_type

    @property
    def mac_addr(self) -> str:
        """The unique mac address of the UIS controller's WI-FI network interface"""
        return self._mac_addr

    @property
    def ports(self) -> list["ACInfinityPort"]:
        """A list of USB-C ports associated with this controller and their associated settings, with or without a UIS child device plugged into it."""
        return self._ports

    @property
    def sensors(self) -> list["ACInfinitySensor"]:
        """A list of USB-C sensors associated with this controller and their associated settings."""
        return self._sensors

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
            case ControllerType.UIS_69_PRO:
                return "UIS Controller 69 Pro (CTR69P)"
            case ControllerType.UIS_69_PRO_PLUS:
                return "UIS Controller 69 Pro+ (CTR69Q)"
            case ControllerType.UIS_89_AI_PLUS:
                return "UIS Controller AI+ (CTR89Q)"
            case _:
                return f"UIS Controller Type {device_type}"


class ACInfinitySensor:
    """
    A USB-C port associated with this controller and its associated settings,
    with or without a UIS child device (fan, light, etc...) plugged into it.
    """

    def __init__(
        self, controller: ACInfinityController, sensor_json: dict[str, Any]
    ) -> None:
        """
        Args:
            controller: The controller that the USB-C port is attached to
            sensor_json: Json of an individual sensor. This is typically obtained from
            the sensor field of a single controller returned from the /api/user/devInfoListAll endpoint.
            See the ports property on ACInfinityController.
        """

        self._controller = controller
        self._sensor_port = sensor_json[SensorPropertyKey.ACCESS_PORT]
        self._sensor_type = sensor_json[SensorPropertyKey.SENSOR_TYPE]

        self._device_info = self.__get_device_info(
            self._controller, self._sensor_port, self._sensor_type
        )

    @staticmethod
    def __get_device_info(
        controller: ACInfinityController, sensor_port: int, sensor_type: int
    ):
        match sensor_type:
            case SensorType.PROBE_TEMPERATURE_F | SensorType.PROBE_TEMPERATURE_C | SensorType.PROBE_HUMIDITY | SensorType.PROBE_VPD:
                return DeviceInfo(
                    identifiers={
                        (DOMAIN, f"{controller.device_id}_{sensor_port}_spc24")
                    },
                    name=f"{controller.device_name} Probe Sensor",
                    manufacturer=MANUFACTURER,
                    via_device=controller.identifier,
                    model="UIS Controller Sensor Probe (AC-SPC24)",
                )
            case SensorType.CO2 | SensorType.LIGHT:
                return DeviceInfo(
                    identifiers={
                        (DOMAIN, f"{controller.device_id}_{sensor_port}_cos3")
                    },
                    name=f"{controller.device_name} CO2 + Light Sensor",
                    manufacturer=MANUFACTURER,
                    via_device=controller.identifier,
                    model="UIS CO2 + Light Sensor (AC-COS3)",
                )
            case SensorType.CONTROLLER_TEMPERATURE_F | SensorType.CONTROLLER_TEMPERATURE_C | SensorType.CONTROLLER_HUMIDITY | SensorType.CONTROLLER_VPD:
                return controller.device_info
            case _:
                return DeviceInfo(
                    identifiers={
                        (
                            DOMAIN,
                            f"{controller.device_id}_{sensor_port}_unknown{sensor_type}",
                        )
                    },
                    name=f"{controller.device_name} Unknown Sensor",
                    manufacturer=MANUFACTURER,
                    via_device=controller.identifier,
                    model=f"UIS Sensor Type {sensor_type}",
                )

    @property
    def controller(self) -> ACInfinityController:
        """The parent controller for this USB-C port"""
        return self._controller

    @property
    def sensor_port(self) -> int:
        """The index of the USB-C sensor port, as labeled on the controller"""
        return self._sensor_port

    @property
    def sensor_type(self) -> int:
        """The type of sensor plugged into the USB-C sensor port"""
        return self._sensor_type

    @property
    def device_info(self) -> DeviceInfo:
        """A HAAS device definition visible in the device manager. Will be a child to the device associated with the parent controller."""
        return self._device_info


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

        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{controller.device_id}_{self._port_index}")},
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
        """The index of the USB-C device port, as labeled on the controller"""
        return self._port_index

    @property
    def port_name(self) -> str:
        """The name of the USB-C device port, as set by the user in the Android/iOS app"""
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

    # api/user/devInfoListAll json organized by controller device id, sensor access port index, and sensor type.
    _sensor_properties: dict[Tuple[str, int, int], Any] = {}

    # api/user/devInfoListAll json organized by controller device id and port index
    _port_properties: dict[Tuple[str, int], Any] = {}

    # api/dev/getDevModeSettingList json organized by controller device id and port index
    _port_controls: dict[Tuple[str, int], Any] = {}

    # api/dev/getDevSetting json organized by controller device id and port (index 0 represents controller settings)
    _device_settings: dict[Tuple[str, int], Any] = {}

    def __init__(self, email: str, password: str) -> None:
        """
        Args:
            email: email address to use to log into the AC Infinity API.  Set by user via config_flow during integration setup
            password: password to use to log into the AC Infinity API.  Set by the user via config_flow during integration setup
        """
        self._client = ACInfinityClient(HOST, email, password)

    def get_controller_property_exists(
        self, controller_id: (str | int), property_key: str
    ) -> bool:
        """returns if a given property exists on a given controller.

        Args:
            controller_id: the device id of the controller
            property_key: the json field name for the data being retrieved
        """
        normalized_id = str(controller_id)
        if normalized_id in self._controller_properties:
            result = self._controller_properties[normalized_id]
            if property_key in result:
                return True
            return property_key in result[ControllerPropertyKey.DEVICE_INFO]

        return False

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
                value = result[property_key]
                return value if value is not None else default_value
            elif property_key in result[ControllerPropertyKey.DEVICE_INFO]:
                value = result[ControllerPropertyKey.DEVICE_INFO][property_key]
                return value if value is not None else default_value

        return default_value

    def get_sensor_property_exists(
        self,
        controller_id: (str | int),
        sensor_port: int,
        sensor_type: int,
        property_key: str,
    ) -> bool:
        """returns if a given sensor property exists on a given controller.

        Args:
            controller_id: the device id of the controller
            sensor_port: the sensor port on the AI controller the sensor is plugged into
            sensor_type: the type of sensor plugged into the port
            property_key: the json field name for the data being retrieved
        """
        normalized_id = (str(controller_id), sensor_port, sensor_type)
        return (
            normalized_id in self._sensor_properties
            and property_key in self._sensor_properties[normalized_id]
        )

    def get_sensor_property(
        self,
        controller_id: (str | int),
        sensor_port: int,
        sensor_type: int,
        property_key: str,
        default_value=None,
    ):
        """gets a property value for a given sensor on a controller, if the property, controller, access port, and sensor all exist.

        Args:
            controller_id:  the device id of the controller
            sensor_port: the index of the sensor port on the controller
            sensor_type: the type of sensor
            property_key: the json filed name for the data being retrieved
            default_value: the default value to return if the controller, port, or property doesn't exist
        """
        normalized_id = (str(controller_id), sensor_port, sensor_type)
        if normalized_id in self._sensor_properties:
            found = self._sensor_properties[normalized_id]
            if property_key in found:
                value = found[property_key]
                return value if value is not None else default_value

        return default_value

    def get_port_property_exists(
        self,
        controller_id: (str | int),
        device_port: int,
        property_key: str,
    ) -> bool:
        """return if a given property key exists on a given device port

        Args:
            controller_id: the device id of the controller
            device_port: the index of the port on the controller
            property_key: the setting to pull the value of
        """
        normalized_id = (str(controller_id), device_port)
        return (
            normalized_id in self._port_properties
            and property_key in self._port_properties[normalized_id]
        )

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

    def get_controller_setting_exists(
        self, controller_id: (str | int), setting_key: str
    ) -> bool:
        """returns if a given setting exists on a given controller.

        Args:
            controller_id: the device id of the controller
            setting_key: the json field name for the data being retrieved
        """
        return self.get_port_setting_exists(controller_id, 0, setting_key)

    def get_controller_setting(
        self, controller_id: (str | int), setting_key: str, default_value=None
    ):
        """gets a property value for a given controller, if both the property and controller exist.

        Args:
            controller_id: the device id of the controller
            setting_key: the json field name for the data being retrieved
            default_value: the value to return if the controller or property doesn't exist
        """
        return self.get_port_setting(controller_id, 0, setting_key, default_value)

    def get_port_setting_exists(
        self, controller_id: (str | int), port_index: int, setting_key: str
    ) -> bool:
        """returns if a given setting exists on a given controller.

        Args:
            controller_id: the device id of the controller
            port_index: the port index of the device.
            setting_key: the json field name for the data being retrieved
        """
        normalized_id = str(controller_id)
        return (
            normalized_id,
            port_index,
        ) in self._device_settings and setting_key in self._device_settings[
            (normalized_id, port_index)
        ]

    def get_port_setting(
        self,
        controller_id: (str | int),
        port_index: int,
        setting_key: str,
        default_value=None,
    ):
        """gets a property value for a given device, if both the setting and device exist.

        Args:
            controller_id: the device id of the controller
            port_index: the port index of the device
            setting_key: the json field name for the data being retrieved
            default_value: the value to return if the controller or property doesn't exist
        """
        normalized_id = str(controller_id)
        if (normalized_id, port_index) in self._device_settings:
            result = self._device_settings[(normalized_id, port_index)]
            if setting_key in result:
                value = result[setting_key]
                return value if value is not None else default_value

        return default_value

    def get_port_control_exists(
        self,
        controller_id: (str | int),
        port_index: int,
        setting_key: str,
    ) -> bool:
        """return if a given setting key exists on a given device port

        Args:
            controller_id: the device id of the controller
            port_index: the index of the port on the controller
            setting_key: the setting to pull the value of
        """
        normalized_id = (str(controller_id), port_index)
        if normalized_id in self._port_controls:
            found = self._port_controls[normalized_id]
            if setting_key in found:
                return True
            return setting_key in found[PortControlKey.DEV_SETTING]

        return False

    def get_port_control(
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
        if normalized_id in self._port_controls:
            result = self._port_controls[normalized_id]
            if setting_key in result:
                value = result[setting_key]
                return value if value is not None else default_value
            elif setting_key in result[PortControlKey.DEV_SETTING]:
                value = result[PortControlKey.DEV_SETTING][setting_key]
                return value if value is not None else default_value

        return default_value

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
                    self._controller_properties[
                        str(controller_id)
                    ] = controller_properties_json

                    # retrieve and set controller settings; temperature, humidity, and vpd offsets
                    controller_settings_json = await self._client.get_device_settings(
                        controller_id, 0
                    )
                    self._device_settings[(controller_id, 0)] = controller_settings_json

                    # controller AI will have a sensor array.
                    if (
                        ControllerPropertyKey.SENSORS
                        in controller_properties_json[ControllerPropertyKey.DEVICE_INFO]
                        and controller_properties_json[
                            ControllerPropertyKey.DEVICE_INFO
                        ][ControllerPropertyKey.SENSORS]
                        is not None
                    ):
                        for sensor_properties_json in controller_properties_json[
                            ControllerPropertyKey.DEVICE_INFO
                        ][ControllerPropertyKey.SENSORS]:
                            access_port_index = sensor_properties_json[
                                SensorPropertyKey.ACCESS_PORT
                            ]
                            sensor_type = sensor_properties_json[
                                SensorPropertyKey.SENSOR_TYPE
                            ]

                            # set sensor properties; sensor value, unit, and display precision
                            self._sensor_properties[
                                (controller_id, access_port_index, sensor_type)
                            ] = sensor_properties_json

                    for port_properties_json in controller_properties_json[
                        ControllerPropertyKey.DEVICE_INFO
                    ][ControllerPropertyKey.PORTS]:
                        port_index = port_properties_json[PortPropertyKey.PORT]

                        # set port properties; current power and remaining time until a mode switch
                        self._port_properties[
                            (controller_id, port_index)
                        ] = port_properties_json

                        # retrieve and set port controls; current mode, temperature triggers, on/off speed, etc...
                        port_controls_json = (
                            await self._client.get_device_mode_settings_list(
                                controller_id, port_index
                            )
                        )
                        self._port_controls[
                            (controller_id, port_index)
                        ] = port_controls_json

                        # retrieve and set port settings; Dynamic Response, Transition values, Buffer values, etc..
                        port_settings_json = await self._client.get_device_settings(
                            controller_id, port_index
                        )
                        self._device_settings[
                            (controller_id, port_index)
                        ] = port_settings_json

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
        self, controller_id: (str | int), key_values: list[Tuple[str, int]]
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller_id: The device id of the controller to update
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        device_name = self.get_controller_property(
            controller_id, ControllerPropertyKey.DEVICE_NAME
        )
        await self.__update_advanced_settings(controller_id, 0, device_name, key_values)

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
            port_index: the port of the device
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
        key_values: list[Tuple[str, int]],
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller_id: The device id of the controller to update
            port_index: the port of the device
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        device_name = self.get_port_property(
            controller_id, port_index, PortPropertyKey.NAME
        )
        await self.__update_advanced_settings(
            controller_id, port_index, device_name, key_values
        )

    async def __update_advanced_settings(
        self,
        controller_id: (str | int),
        port: int,
        device_name: str,
        key_values: list[Tuple[str, int]],
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller_id: The device id of the controller to update
            port: 0 for controller settings, or the port number for port settings
            device_name: The current controller name value as it exists in the coordinator from the last refresh call.
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        try_count = 0
        while True:
            try:
                await self._client.update_advanced_settings(
                    controller_id, port, device_name, key_values
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

    async def update_port_control(
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
        await self.update_port_controls(
            controller_id, port_index, [(setting_key, new_value)]
        )

    async def update_port_controls(
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

    def __init__(self, coordinator: ACInfinityDataUpdateCoordinator, platform: str):
        super().__init__(coordinator)
        self._platform_name = platform

    def __repr__(self):
        return f"<ACInfinityEntity unique_id={self.unique_id}>"

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

    @property
    @abstractmethod
    def is_suitable(self) -> bool:
        """Returns true if the field's backing key exists in the initial data obtained"""

    @property
    def platform_name(self) -> str:
        return self._platform_name


class ACInfinityControllerEntity(ACInfinityEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        controller: ACInfinityController,
        suitable_fn: Callable[[ACInfinityEntity, ACInfinityController], bool],
        data_key: str,
        platform: str,
    ):
        super().__init__(coordinator, platform)
        self._controller = controller
        self._data_key = data_key
        self._suitable_fn = suitable_fn

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

    @property
    def is_suitable(self) -> bool:
        return self._suitable_fn(self, self.controller)


class ACInfinitySensorEntity(ACInfinityEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        sensor: ACInfinitySensor,
        suitable_fn: Callable[[ACInfinityEntity, ACInfinitySensor], bool],
        platform: str,
    ):
        super().__init__(coordinator, platform)
        self._sensor = sensor
        self._suitable_fn = suitable_fn

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""
        return f"{DOMAIN}_{self._sensor.controller.mac_addr}_sensor_{self._sensor.sensor_port}_{self.entity_description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Returns the device info for the port entity"""
        return self._sensor.device_info

    @property
    def sensor(self) -> ACInfinitySensor:
        return self._sensor

    @property
    def is_suitable(self) -> bool:
        return self._suitable_fn(self, self.sensor)


class ACInfinityPortEntity(ACInfinityEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        port: ACInfinityPort,
        suitable_fn: Callable[[ACInfinityEntity, ACInfinityPort], bool],
        data_key: str,
        platform: str,
    ):
        super().__init__(coordinator, platform)
        self._port = port
        self._suitable_fn = suitable_fn
        self._data_key = data_key

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

    @property
    def is_suitable(self) -> bool:
        return self._suitable_fn(self, self.port)


@dataclass
class ACInfinityControllerReadOnlyMixin:
    """Mixin for retrieving values for controller level sensors"""

    suitable_fn: Callable[[ACInfinityEntity, ACInfinityController], bool]
    """Input data object and a device id; output if suitable"""
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
class ACInfinitySensorReadOnlyMixin:
    """Mixin for retrieving values for controller level sensors"""

    suitable_fn: Callable[[ACInfinityEntity, ACInfinitySensor], bool]
    """Input data object and a device id; output if suitable"""
    get_value_fn: Callable[[ACInfinityEntity, ACInfinitySensor], StateType]
    """Input data object and a device id; output the value."""


@dataclass
class ACInfinityPortReadOnlyMixin:
    """Mixin for retrieving values for port device level sensors"""

    suitable_fn: Callable[[ACInfinityEntity, ACInfinityPort], bool]
    """Input data object, device id, and port number; output if suitable."""
    get_value_fn: Callable[[ACInfinityEntity, ACInfinityPort], StateType]
    """Input data object, device id, and port number; output the value."""


@dataclass
class ACInfinityPortReadWriteMixin(ACInfinityPortReadOnlyMixin):
    """Mixin for retrieving and updating values for port device level settings"""

    set_value_fn: Callable[
        [ACInfinityEntity, ACInfinityPort, StateType], Awaitable[None]
    ]
    """Input data object, device id, port number, and desired value."""


class ACInfinityEntities(list[ACInfinityEntity]):
    def append_if_suitable(self, entity: ACInfinityEntity):
        if entity.is_suitable:
            self.append(entity)
            _LOGGER.info(
                'Initializing entity "%s" (%s) for platform "%s".',
                entity.unique_id,
                entity.translation_key,
                entity.platform_name,
            )
        else:
            _LOGGER.warning(
                'Ignoring unsuitable entity "%s" (%s) for platform "%s".',
                entity.unique_id,
                entity.translation_key,
                entity.platform_name,
            )
