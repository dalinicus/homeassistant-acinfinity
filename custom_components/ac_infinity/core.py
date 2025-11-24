import asyncio
import json
import logging
from abc import abstractmethod, ABC
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable

import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from custom_components.ac_infinity.client import ACInfinityClient, ACInfinityClientInvalidAuth, \
    ACInfinityClientCannotConnect, ACInfinityClientRequestFailed
from .const import (
    AI_CONTROLLER_TYPES,
    DOMAIN,
    MANUFACTURER,
    ControllerPropertyKey,
    ControllerType,
    DeviceControlKey,
    DevicePropertyKey,
    SensorPropertyKey,
    SensorType,
    ConfigurationKey,
    EntityConfigValue,
)

ACINFINITY_API_ERROR = "Retry limit exceeded contacting the AC Infinity API.  The AC Infinity API can be unstable; Please try your request again later."

_LOGGER = logging.getLogger(__name__)


class ACInfinityController:
    """
    A UIS enabled AC Infinity Controller
    """

    def __init__(
        self, controller_json: dict[str, Any]
    ) -> None:
        """
        Args:
            controller_json: Json of an individual controller. This is typically obtained from
            /api/user/devInfoListAll endpoint, and would be a single object obtained from the array
            in the data field of the json returned.
        """

        self._controller_id = str(controller_json[ControllerPropertyKey.DEVICE_ID])
        self._mac_addr = controller_json[ControllerPropertyKey.MAC_ADDR]
        self._controller_name = controller_json[ControllerPropertyKey.DEVICE_NAME]
        self._controller_type = controller_json[ControllerPropertyKey.DEVICE_TYPE]
        self._identifier = (DOMAIN, self._controller_id)

        devices = controller_json[ControllerPropertyKey.DEVICE_INFO][ControllerPropertyKey.PORTS] or []
        self._devices = [ACInfinityDevice(self, device)for device in devices]

        self._device_info = DeviceInfo(
            identifiers={self._identifier},
            name=self._controller_name,
            manufacturer=MANUFACTURER,
            hw_version=controller_json[ControllerPropertyKey.HW_VERSION],
            sw_version=controller_json[ControllerPropertyKey.SW_VERSION],
            model=self.__get_device_model_by_device_type(
                controller_json[ControllerPropertyKey.DEVICE_TYPE]
            ),
        )

        # controller AI will have a sensor array.
        self._sensors = []
        if ControllerPropertyKey.SENSORS in controller_json[ControllerPropertyKey.DEVICE_INFO]:
            sensors = controller_json[ControllerPropertyKey.DEVICE_INFO][ControllerPropertyKey.SENSORS] or []
            self._sensors = [ACInfinitySensor(self, sensor) for sensor in sensors]

    @property
    def controller_id(self) -> str:
        """The unique identifier of the UIS Controller"""
        return self._controller_id

    @property
    def controller_name(self) -> str:
        """The name of the controller as set in the Android/iOS app"""
        return self._controller_name

    @property
    def is_ai_controller(self) -> bool:
        """Returns true if this controller is an AI controller"""
        return self._controller_type in AI_CONTROLLER_TYPES

    @property
    def mac_addr(self) -> str:
        """The unique mac address of the UIS controller's WI-FI network interface"""
        return self._mac_addr

    @property
    def devices(self) -> list["ACInfinityDevice"]:
        """A list of USB-C ports associated with this controller and their associated settings, with or without a UIS child device plugged into it."""
        return self._devices

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
            case ControllerType.UIS_OUTLET_AI:
                return "UIS Controller Outlet AI (AC-ADA4)"
            case ControllerType.UIS_OUTLET_AI_PLUS:
                return "UIS Controller Outlet AI+ (AC-ADA8)"
            case _:
                return f"UIS Controller Type {device_type}"


class ACInfinitySensor:
    """
    A USB-C port associated with this controller and its associated settings,
    with or without a UIS child device (fan, light, etc...) plugged into it.
    """

    def __init__(self, controller: ACInfinityController, sensor_json: dict[str, Any]) -> None:
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
        match int(sensor_type):
            case (
                SensorType.PROBE_TEMPERATURE_F
                | SensorType.PROBE_TEMPERATURE_C
                | SensorType.PROBE_HUMIDITY
                | SensorType.PROBE_VPD
            ):
                return DeviceInfo(
                    identifiers={
                        (DOMAIN, f"{controller.controller_id}_{sensor_port}_spc24")
                    },
                    name=f"{controller.controller_name} Probe Sensor",
                    manufacturer=MANUFACTURER,
                    via_device=controller.identifier,
                    model="UIS Controller Sensor Probe (AC-SPC24)",
                )
            case SensorType.CO2 | SensorType.LIGHT:
                return DeviceInfo(
                    identifiers={
                        (DOMAIN, f"{controller.controller_id}_{sensor_port}_cos3")
                    },
                    name=f"{controller.controller_name} CO2 + Light Sensor",
                    manufacturer=MANUFACTURER,
                    via_device=controller.identifier,
                    model="UIS CO2 + Light Sensor (AC-COS3)",
                )
            case SensorType.WATER:
                return DeviceInfo(
                    identifiers={
                        (DOMAIN, f"{controller.controller_id}_{sensor_port}_wds3")
                    },
                    name=f"{controller.controller_name} Water Sensor",
                    manufacturer=MANUFACTURER,
                    via_device=controller.identifier,
                    model="UIS Water Sensor (AC-WDS3)",
                )
            case SensorType.SOIL:
                return DeviceInfo(
                    identifiers={
                        (DOMAIN, f"{controller.controller_id}_{sensor_port}_sls3")
                    },
                    name=f"{controller.controller_name} Soil Sensor",
                    manufacturer=MANUFACTURER,
                    via_device=controller.identifier,
                    model="UIS Soil Sensor (AC-SLS3)",
                )
            case (
                SensorType.CONTROLLER_TEMPERATURE_F
                | SensorType.CONTROLLER_TEMPERATURE_C
                | SensorType.CONTROLLER_HUMIDITY
                | SensorType.CONTROLLER_VPD
            ):
                return controller.device_info
            case _:
                return DeviceInfo(
                    identifiers={
                        (DOMAIN, f"{controller.controller_id}_{sensor_port}_unknown{sensor_type}")
                    },
                    name=f"{controller.controller_name} Unknown Sensor",
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


class ACInfinityDevice:
    """
    A USB-C port associated with this controller and its associated settings,
    with or without a UIS child device (fan, light, etc...) plugged into it.
    """

    def __init__(
        self, controller: ACInfinityController, device_json: dict[str, Any]
    ) -> None:
        """
        Args:
            controller: The controller that the USB-C port is attached to
            device_json: Json of an individual controller. This is typically obtained from
            the ports field of a single controller returned from the /api/user/devInfoListAll endpoint.
            See the ports property on ACInfinityController.
        """

        self._controller = controller
        self._device_port = device_json[DevicePropertyKey.PORT]
        self._device_name = device_json[DevicePropertyKey.NAME]

        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{controller.controller_id}_{self._device_port}")},
            name=f"{controller.controller_name} {self.device_name}",
            manufacturer=MANUFACTURER,
            via_device=controller.identifier,
            model="UIS Enabled Device",
        )

    @property
    def controller(self) -> ACInfinityController:
        """The parent controller for this USB-C port"""
        return self._controller

    @property
    def device_port(self) -> int:
        """The index of the USB-C device port, as labeled on the controller"""
        return self._device_port

    @property
    def device_name(self) -> str:
        """The name of the USB-C device port, as set by the user in the Android/iOS app"""
        return self._device_name

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
    _sensor_properties: dict[tuple[str, int, int], Any] = {}

    # api/user/devInfoListAll json organized by controller device id and port index
    _device_properties: dict[tuple[str, int], Any] = {}

    # api/dev/getDevModeSettingList json organized by controller device id and port index
    _device_controls: dict[tuple[str, int], Any] = {}

    # api/dev/getDevSetting json organized by controller device id and port (index 0 represents controller settings)
    _device_settings: dict[tuple[str, int], Any] = {}

    def __init__(
        self, client: ACInfinityClient
    ) -> None:
        """
        Args:
            client: The http client to use to make requests to the AC Infinity API
        """
        self._client = client

    def get_device_ids(self) -> list[str]:
        """
        returns a list of devices associated with the account
        """
        return list(self._controller_properties.keys())

    def get_controller_property_exists(
        self, controller_id: str | int, property_key: str
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
        self, controller_id: str | int, property_key: str, default_value=None
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
        controller_id: str | int,
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
        controller_id: str | int,
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

    def get_device_property_exists(
        self,
        controller_id: str | int,
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
            normalized_id in self._device_properties
            and property_key in self._device_properties[normalized_id]
        )

    def get_device_property(
        self,
        controller_id: str | int,
        device_port: int,
        property_key: str,
        default_value=None,
    ):
        """gets a property value for a given port on a controller, if the property, controller and port all exist.

        Args:
            controller_id:  the device id of the controller
            device_port: the index of the port on the controller
            property_key: the json filed name for the data being retrieved
            default_value: the default value to return if the controller, port, or property doesn't exist
        """
        normalized_id = (str(controller_id), device_port)
        if normalized_id in self._device_properties:
            found = self._device_properties[normalized_id]
            if property_key in found:
                value = found[property_key]
                return value if value is not None else default_value

        return default_value

    def get_controller_setting_exists(
        self, controller_id: str | int, setting_key: str
    ) -> bool:
        """returns if a given setting exists on a given controller.

        Args:
            controller_id: the device id of the controller
            setting_key: the json field name for the data being retrieved
        """
        return self.get_device_setting_exists(controller_id, 0, setting_key)

    def get_controller_setting(
        self, controller_id: str | int, setting_key: str, default_value=None
    ):
        """gets a property value for a given controller, if both the property and controller exist.

        Args:
            controller_id: the device id of the controller
            setting_key: the json field name for the data being retrieved
            default_value: the value to return if the controller or property doesn't exist
        """
        return self.get_device_setting(controller_id, 0, setting_key, default_value)

    def get_device_setting_exists(
        self, controller_id: str | int, device_port: int, setting_key: str
    ) -> bool:
        """returns if a given setting exists on a given controller.

        Args:
            controller_id: the device id of the controller
            device_port: the port index of the device.
            setting_key: the json field name for the data being retrieved
        """
        normalized_id = (str(controller_id), device_port)
        return normalized_id in self._device_settings and setting_key in self._device_settings[normalized_id]

    def get_device_setting(
        self,
        controller_id: str | int,
        device_port: int,
        setting_key: str,
        default_value=None,
    ):
        """gets a property value for a given device, if both the setting and device exist.

        Args:
            controller_id: the device id of the controller
            device_port: the port index of the device
            setting_key: the json field name for the data being retrieved
            default_value: the value to return if the controller or property doesn't exist
        """
        normalized_id = str(controller_id)
        if (normalized_id, device_port) in self._device_settings:
            result = self._device_settings[(normalized_id, device_port)]
            if setting_key in result:
                value = result[setting_key]
                return value if value is not None else default_value

        return default_value

    def get_device_control_exists(
        self,
        controller_id: str | int,
        device_port: int,
        setting_key: str,
    ) -> bool:
        """return if a given setting key exists on a given device port

        Args:
            controller_id: the device id of the controller
            device_port: the index of the port on the controller
            setting_key: the setting to pull the value of
        """
        normalized_id = (str(controller_id), device_port)
        if normalized_id in self._device_controls:
            found = self._device_controls[normalized_id]
            if setting_key in found:
                return True
            return setting_key in found[DeviceControlKey.DEV_SETTING]

        return False

    def get_device_control(
        self,
        controller_id: str | int,
        device_port: int,
        setting_key: str,
        default_value=None,
    ):
        """gets the current set value for a given device setting

        Args:
            controller_id: the device id of the controller
            device_port: the index of the port on the controller
            setting_key: the setting to pull the value of
            default_value: the default value to return if the controller, port, or setting doesn't exist
        """
        normalized_id = (str(controller_id), device_port)
        if normalized_id in self._device_controls:
            result = self._device_controls[normalized_id]
            if setting_key in result:
                value = result[setting_key]
                return value if value is not None else default_value
            elif setting_key in result[DeviceControlKey.DEV_SETTING]:
                value = result[DeviceControlKey.DEV_SETTING][setting_key]
                return value if value is not None else default_value

        return default_value

    async def refresh(self) -> None:
        """refreshes the values of properties and settings from the AC infinity API"""
        try_count = 0
        while True:
            try:
                if not self._client.is_logged_in():
                    await self._client.login()

                all_devices_json = await self._client.get_account_controllers()
                for controller_properties_json in all_devices_json:
                    controller_id = controller_properties_json[ControllerPropertyKey.DEVICE_ID]

                    # set controller properties; readings for temp, vpd, humidity, etc...
                    self._controller_properties[str(controller_id)] = controller_properties_json

                    # retrieve and set controller settings; temperature, humidity, and vpd offsets
                    controller_settings_json = await self._client.get_device_mode_settings(controller_id, 0)
                    self._device_settings[(controller_id, 0)] = controller_settings_json[DeviceControlKey.DEV_SETTING]

                    # controller AI will have a sensor array.
                    if ControllerPropertyKey.SENSORS in controller_properties_json[ControllerPropertyKey.DEVICE_INFO]:
                        sensors = controller_properties_json[ControllerPropertyKey.DEVICE_INFO][ControllerPropertyKey.SENSORS] or []
                        for sensor_properties_json in sensors:
                            access_port_index = sensor_properties_json[SensorPropertyKey.ACCESS_PORT]
                            sensor_type = sensor_properties_json[SensorPropertyKey.SENSOR_TYPE]

                            # set sensor properties; sensor value, unit, and display precision
                            self._sensor_properties[(controller_id, access_port_index, sensor_type)] = sensor_properties_json

                    for device_properties_json in controller_properties_json[ControllerPropertyKey.DEVICE_INFO][ControllerPropertyKey.PORTS]:
                        device_port = device_properties_json[DevicePropertyKey.PORT]

                        # set port properties; current power and remaining time until a mode switch
                        self._device_properties[(controller_id, device_port)] = device_properties_json

                        # retrieve and set port controls; current mode, temperature triggers, on/off speed, etc...
                        device_controls_json = await self._client.get_device_mode_settings(controller_id, device_port)
                        self._device_controls[(controller_id, device_port)] = device_controls_json

                        # retrieve and set port settings; Dynamic Response, Transition values, Buffer values, etc..
                        device_settings_json = await self._client.get_device_mode_settings(controller_id, device_port)
                        self._device_settings[(controller_id, device_port)] = device_settings_json[DeviceControlKey.DEV_SETTING]

                return  # update successful.  eject from the infinite while loop.

            except (
                ACInfinityClientCannotConnect,
                ACInfinityClientRequestFailed,
                aiohttp.ClientError,
                asyncio.TimeoutError
            ) as ex:
                if try_count < 4:
                    try_count += 1
                    _LOGGER.warning("Unable to refresh from data update coordinator. Retry attempt %s/4", str(try_count))
                    await asyncio.sleep(1)
                else:
                    _LOGGER.error(ACINFINITY_API_ERROR, exc_info=ex)
                    raise
            except ACInfinityClientInvalidAuth as ex:
                _LOGGER.error("Unable to refresh from data update coordinator: Authentication failed", exc_info=ex)
                raise
            except Exception as ex:
                _LOGGER.error("Unable to refresh from data update coordinator: Unexpected error", exc_info=ex)
                raise

    def get_all_controller_properties(self) -> list[ACInfinityController]:
        """gets device metadata, such as ids, labels, macaddr, etc... that are not expected to change"""
        if self._controller_properties is None:
            return []

        return [ACInfinityController(device) for device in self._controller_properties.values()]

    async def update_controller_setting(
        self,
        controller: ACInfinityController,
        setting_key: str,
        new_value: int,
    ):
        """Update the value of a setting via the AC Infinity API

        Args:
            controller: the controller
            setting_key: the setting to update the value of
            new_value: the new value of the setting to set
        """
        await self.update_controller_settings(controller, {setting_key: new_value})

    async def update_controller_settings(
        self, controller: ACInfinityController, key_values: dict[str, int]
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller: controller to update
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        if controller.is_ai_controller:
            raise NotImplementedError("AI controllers do not support updating controller settings: %s", key_values)
        else:
            await self.__update_advanced_settings(controller.controller_id, 0, controller.controller_name, key_values)

    async def update_device_setting(
        self,
        device: ACInfinityDevice,
        setting_key: str,
        new_value: int,
    ):
        """Update the value of a setting via the AC Infinity API

        Args:
            device: the device
            setting_key: the setting to update the value of
            new_value: the new value of the setting to set
        """
        await self.update_device_settings(device, {setting_key: new_value})

    async def update_device_settings(
        self,
        device: ACInfinityDevice,
        key_values: dict[str, int],
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            device: the device
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        if device.controller.is_ai_controller:
            await self.__update_ai_control_and_settings(device.controller.controller_id, device.device_port, key_values)
        else:
            await self.__update_advanced_settings(device.controller.controller_id, device.device_port, device.device_name, key_values)

    async def update_device_control(
        self,
        device: ACInfinityDevice,
        setting_key: str,
        new_value: int,
    ):
        """Update the value of a setting via the AC Infinity API

        Args:
            device: the index of the port on the controller
            setting_key: the setting to update the value of
            new_value: the new value of the setting to set
        """
        await self.update_device_controls(device, {setting_key: new_value})

    async def update_device_controls(
        self,
        device: ACInfinityDevice,
        key_values: dict[str, int],
    ):
        if device.controller.is_ai_controller:
            await self.__update_ai_control_and_settings(device.controller.controller_id, device.device_port, key_values)
        else:
            await self.__update_device_controls(device.controller.controller_id, device.device_port, key_values)

    async def __update_device_controls(
        self,
        controller_id: str | int,
        device_port: int,
        key_values: dict[str, int],
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller_id: the device id of the controller
            device_port: the index of the port on the controller
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        try_count = 0
        while True:
            try:
                await self._client.update_device_controls(controller_id, device_port, key_values)
                return

            except (
                ACInfinityClientCannotConnect,
                ACInfinityClientRequestFailed,
                aiohttp.ClientError,
                asyncio.TimeoutError
            ) as ex:

                if try_count < 4:
                    try_count += 1
                    _LOGGER.warning("Unable to update device controls. Retry attempt %s/4", str(try_count))
                    await asyncio.sleep(1)
                else:
                    _LOGGER.error(ACINFINITY_API_ERROR, exc_info=ex)
                    raise
            except ACInfinityClientInvalidAuth as ex:
                _LOGGER.error("Unable to update device controls: Authentication failed", exc_info=ex)
                raise
            except Exception as ex:
                _LOGGER.error("Unable to update device controls: Unexpected error", exc_info=ex)
                raise

    async def __update_advanced_settings(
        self,
        controller_id: str | int,
        device_port: int,
        device_name: str,
        key_values: dict[str, int],
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller_id: The device id of the controller to update
            device_port: 0 for controller settings, or the port number for port settings
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        try_count = 0
        while True:
            try:
                await self._client.update_device_settings(controller_id, device_port, device_name, key_values)
                return

            except (
                ACInfinityClientCannotConnect,
                ACInfinityClientRequestFailed,
                aiohttp.ClientError,
                asyncio.TimeoutError
            ) as ex:
                if try_count < 4:
                    try_count += 1
                    _LOGGER.warning("Unable to update advanced controller settings. Retry attempt %s/4", str(try_count))
                    await asyncio.sleep(1)
                else:
                    _LOGGER.error(ACINFINITY_API_ERROR, exc_info=ex)
                    raise
            except ACInfinityClientInvalidAuth as ex:
                _LOGGER.error("Unable to update advanced controller settings: Authentication failed", exc_info=ex)
                raise
            except Exception as ex:
                _LOGGER.error("Unable to update advanced controller settings: Unexpected error", exc_info=ex)
                raise

    async def __update_ai_control_and_settings(
        self,
        controller_id: str | int,
        device_port: int,
        key_values: dict[str, int],
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller_id: the device id of the controller
            device_port: the index of the port on the controller
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        try_count = 0
        while True:
            try:
                await self._client.update_ai_device_control_and_settings(controller_id, device_port, key_values)
                return

            except (
                ACInfinityClientCannotConnect,
                ACInfinityClientRequestFailed,
                aiohttp.ClientError,
                asyncio.TimeoutError
            ) as ex:

                if try_count < 4:
                    try_count += 1
                    _LOGGER.warning("Unable to update ai device controls and settings. Retry attempt %s/4", str(try_count))
                    await asyncio.sleep(1)
                else:
                    _LOGGER.error(ACINFINITY_API_ERROR, exc_info=ex)
                    raise
            except ACInfinityClientInvalidAuth as ex:
                _LOGGER.error("Unable to update ai device controls and settings: Authentication failed", exc_info=ex)
                raise
            except Exception as ex:
                _LOGGER.error("Unable to update ai device controls and settings: Unexpected error", exc_info=ex)
                raise

    async def close(self) -> None:
        """Close the client session when done"""
        if self._client:
            await self._client.close()


class ACInfinityDataUpdateCoordinator(DataUpdateCoordinator):
    """Handles updating data for the integration"""

    def __init__(
        self,
        hass,
        entry: ConfigEntry,
        service: ACInfinityService,
        polling_interval: int,
    ):
        """Constructor"""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
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
            raise UpdateFailed from e

    @property
    def ac_infinity(self) -> ACInfinityService:
        return self._ac_infinity


class ACInfinityEntity(CoordinatorEntity[ACInfinityDataUpdateCoordinator], ABC):
    _attr_has_entity_name = True
    coordinator: ACInfinityDataUpdateCoordinator
    translation_key: str

    def __init__(
        self, coordinator: ACInfinityDataUpdateCoordinator, platform: str, data_key: str
    ):
        super().__init__(coordinator)
        self._platform_name = platform
        self._data_key = data_key

    def __repr__(self):
        return f"<ACInfinityEntity unique_id={self.unique_id}>"

    @property
    def data_key(self) -> str:
        """Returns the underlying ac_infinity api data key used to track the data"""
        return self._data_key

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

    @abstractmethod
    def is_enabled(self, entry: ConfigEntry) -> bool:
        """Returns true if the entity is enabled via options flowd"""

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
        enabled_fn: Callable[[ConfigEntry, str, str], bool],
        suitable_fn: Callable[[ACInfinityEntity, ACInfinityController], bool],
        data_key: str,
        platform: str,
    ):
        super().__init__(coordinator, platform, data_key)
        self._controller = controller
        self._enabled_fn = enabled_fn
        self._suitable_fn = suitable_fn

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""
        return f"{DOMAIN}_{self._controller.mac_addr}_{self.data_key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Returns the device info for the controller entity"""
        return self._controller.device_info

    @property
    def controller(self) -> ACInfinityController:
        return self._controller

    def is_enabled(self, entry: ConfigEntry) -> bool:
        return self._enabled_fn(entry, str(self._controller.controller_id), "controller")

    @property
    def is_suitable(self) -> bool:
        return self._suitable_fn(self, self.controller)


class ACInfinitySensorEntity(ACInfinityEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        sensor: ACInfinitySensor,
        enabled_fn: Callable[[ConfigEntry, str, str], bool],
        suitable_fn: Callable[[ACInfinityEntity, ACInfinitySensor], bool],
        data_key: str,
        platform: str,
    ):
        super().__init__(coordinator, platform, data_key)
        self._sensor = sensor
        self._enabled_fn = enabled_fn
        self._suitable_fn = suitable_fn

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""
        return f"{DOMAIN}_{self._sensor.controller.mac_addr}_sensor_{self._sensor.sensor_port}_{self.data_key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Returns the device info for the port entity"""
        return self._sensor.device_info

    @property
    def sensor(self) -> ACInfinitySensor:
        return self._sensor

    def is_enabled(self, entry: ConfigEntry) -> bool:
        return self._enabled_fn(entry, str(self._sensor.controller.controller_id), "sensors")

    @property
    def is_suitable(self) -> bool:
        return self._suitable_fn(self, self.sensor)


class ACInfinityDeviceEntity(ACInfinityEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        enabled_fn: Callable[[ConfigEntry, str, str], bool],
        suitable_fn: Callable[[ACInfinityEntity, ACInfinityDevice], bool],
        at_type_fn: Callable[[int], bool] | None,
        data_key: str,
        platform: str,
    ):
        super().__init__(coordinator, platform, data_key)
        self._device = device
        self._enabled_fn = enabled_fn
        self._suitable_fn = suitable_fn
        self._at_type_fn = at_type_fn

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""
        return f"{DOMAIN}_{self._device.controller.mac_addr}_port_{self._device.device_port}_{self.data_key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Returns the device info for the port entity"""
        return self._device.device_info

    @property
    def device_port(self) -> ACInfinityDevice:
        return self._device

    def is_enabled(self, entry: ConfigEntry) -> bool:
        return self._enabled_fn(entry, str(self._device.controller.controller_id), f"port_{self._device.device_port}")

    @property
    def is_suitable(self) -> bool:
        return self._suitable_fn(self, self.device_port)

    @property
    def available(self) -> bool:
        """Returns true if the device is online and, if provided, the active mode matches the at_type filter"""
        active_at_type = self.ac_infinity.get_device_control(
            self._device.controller.controller_id,
            self.device_port.device_port,
            DeviceControlKey.AT_TYPE
        )
        return super().available and self.ac_infinity.get_device_property(
            self._device.controller.controller_id,
            self.device_port.device_port,
            DevicePropertyKey.ONLINE
        ) == 1 and (self._at_type_fn is None or self._at_type_fn(active_at_type))


@dataclass(frozen=True)
class ACInfinityBaseMixin:
    enabled_fn: Callable[[ConfigEntry, str, str], bool]
    """ output if the entity is enabled via option flow"""


@dataclass(frozen=True)
class ACInfinityControllerReadOnlyMixin[T](ACInfinityBaseMixin):
    """Mixin for retrieving values for controller level sensors"""

    suitable_fn: Callable[[ACInfinityEntity, ACInfinityController], bool]
    """Input data object and a device id; output if suitable"""
    get_value_fn: Callable[[ACInfinityEntity, ACInfinityController], T]
    """Input data object and a device id; output the value."""


@dataclass(frozen=True)
class ACInfinityControllerReadWriteMixin[T](ACInfinityControllerReadOnlyMixin[T]):
    """Mixin for retrieving and updating values for controller level settings"""

    set_value_fn: Callable[[ACInfinityEntity, ACInfinityController, T], Awaitable[None]]
    """Input data object, device id, port number, and desired value."""


@dataclass(frozen=True)
class ACInfinitySensorReadOnlyMixin[T](ACInfinityBaseMixin):
    """Mixin for retrieving values for controller level sensors"""
    suitable_fn: Callable[[ACInfinityEntity, ACInfinitySensor], bool]
    """Input data object and a device id; output if suitable"""
    get_value_fn: Callable[[ACInfinityEntity, ACInfinitySensor], T]
    """Input data object and a device id; output the value."""


@dataclass(frozen=True)
class ACInfinityDeviceReadOnlyMixin[T](ACInfinityBaseMixin):
    """Mixin for retrieving values for port device level sensors"""
    suitable_fn: Callable[[ACInfinityEntity, ACInfinityDevice], bool]
    """Input data object, device id, and port number; output if suitable."""
    get_value_fn: Callable[[ACInfinityEntity, ACInfinityDevice], T]
    """Input data object, device id, and port number; output the value."""


@dataclass(frozen=True)
class ACInfinityDeviceReadWriteMixin[T](ACInfinityDeviceReadOnlyMixin[T]):
    """Mixin for retrieving and updating values for port device level settings"""
    set_value_fn: Callable[[ACInfinityEntity, ACInfinityDevice, T], Awaitable[None]]
    """Input data object, device id, port number, and desired value."""
    at_type_fn: Callable[[int], bool] | None
    """Function that accepts the active at_type and returns True if the entity should be available for that mode"""


class ACInfinityEntities(list[ACInfinityEntity]):
    def __init__(self, config: ConfigEntry):
        super().__init__()
        self._config_entry = config

    def append_if_suitable(self, entity: ACInfinityEntity):

        if entity.is_enabled(self._config_entry):
            if entity.is_suitable:
                self.append(entity)
                _LOGGER.debug(
                    'Initializing entity "%s" (%s) for platform "%s".',
                    entity.unique_id,
                    entity.translation_key,
                    entity.platform_name,
                )
            else:
                _LOGGER.debug(
                    'Ignoring unsuitable entity "%s" (%s) for platform "%s". (Not applicable for device)',
                    entity.unique_id,
                    entity.translation_key,
                    entity.platform_name,
                )
        else:
            _LOGGER.debug(
                'Ignoring disabled entity "%s" (%s) for platform "%s". (Disabled by user)',
                entity.unique_id,
                entity.translation_key,
                entity.platform_name,
            )


def enabled_fn_sensor(entry: ConfigEntry, device_id: str, entity_config_key: str) -> bool:
    return entry.data[ConfigurationKey.ENTITIES][device_id][entity_config_key] != EntityConfigValue.Disable


def enabled_fn_control(entry: ConfigEntry, device_id: str, entity_config_key: str) -> bool:
    setting = entry.data[ConfigurationKey.ENTITIES][device_id][entity_config_key]
    return setting == EntityConfigValue.All or setting == EntityConfigValue.SensorsAndControls


def enabled_fn_setting(entry: ConfigEntry, device_id: str, entity_config_key: str) -> bool:
    setting = entry.data[ConfigurationKey.ENTITIES][device_id][entity_config_key]
    return setting == EntityConfigValue.All or setting == EntityConfigValue.SensorsAndSettings

