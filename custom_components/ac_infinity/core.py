import asyncio
import json
import logging
from abc import abstractmethod, ABC
from collections.abc import Awaitable, Iterable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Callable

import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from custom_components.ac_infinity.client import ACInfinityClient, ACInfinityClientInvalidAuth, \
    ACInfinityClientCannotConnect, ACInfinityClientRequestFailed
from .const import (
    AtType,
    AI_CONTROLLER_TYPES,
    ROOM_TO_ROOM_FAN_CONTROLLER_TYPES,
    ROOM_TO_ROOM_FAN_DISPLAY_SETTING_TRIGGER_KEYS,
    AIRTAP_CONTROLLER_KEYS,
    AIRTAP_CONTROLLER_TYPES,
    AIRTAP_DEVICE_KEYS,
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
        self._is_airtap = ACInfinityController.is_airtap_json(controller_json)

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

        # devices are created last; a portless fan's port 0 device shares this controller's device info.
        self._devices = [
            ACInfinityDevice(self, device) for device in ACInfinityController.get_port_jsons(controller_json)
        ]

    @staticmethod
    def is_airtap_json(controller_json: dict[str, Any]) -> bool:
        """Returns true if the devInfoListAll json describes an AIRTAP register fan"""
        return bool(controller_json.get(ControllerPropertyKey.IS_AIRTAP)) or (
            controller_json.get(ControllerPropertyKey.DEVICE_TYPE) in AIRTAP_CONTROLLER_TYPES
        )

    @staticmethod
    def get_port_jsons(controller_json: dict[str, Any]) -> list[dict[str, Any]]:
        """Returns the port json objects of a controller from its devInfoListAll json.

        AIRTAP register fans and room-to-room fans have no ports; the fan itself is exposed as port 0
        so the port level mode and speed entities apply to it.  An AIRTAP's deviceInfo already carries
        the port style fields (speak, online, remainTime, ...), so it is reused as the port json.
        A room-to-room fan's port 0 properties are derived from its mode settings during refresh.

        Some controllers (e.g. a 69 Pro on firmware 3.2.56) report ports as null while still reporting
        a port count; their mode settings are still available per port, so placeholder ports are used.
        """
        device_info = controller_json[ControllerPropertyKey.DEVICE_INFO]
        ports = device_info.get(ControllerPropertyKey.PORTS) or []
        if ports:
            return ports
        if ACInfinityController.is_airtap_json(controller_json):
            return [{
                **device_info,
                DevicePropertyKey.PORT: 0,
                DevicePropertyKey.NAME: controller_json[ControllerPropertyKey.DEVICE_NAME],
            }]
        if controller_json.get(ControllerPropertyKey.DEVICE_TYPE) in ROOM_TO_ROOM_FAN_CONTROLLER_TYPES:
            return [{
                DevicePropertyKey.PORT: 0,
                DevicePropertyKey.NAME: "Main",
                DevicePropertyKey.SPEAK: 0,
                DevicePropertyKey.ONLINE: controller_json.get(ControllerPropertyKey.ONLINE, 0),
                DevicePropertyKey.STATE: 0,
                DevicePropertyKey.REMAINING_TIME: 0,
            }]
        return [
            {
                DevicePropertyKey.PORT: port,
                DevicePropertyKey.NAME: f"Port {port}",
                DevicePropertyKey.ONLINE: controller_json.get(ControllerPropertyKey.ONLINE, 0),
            }
            for port in range(1, (controller_json.get(ControllerPropertyKey.PORT_COUNT) or 0) + 1)
        ]

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
    def is_room_to_room_fan(self) -> bool:
        """Returns true if this is a standalone room-to-room/through-wall fan (e.g. AC-TWT6)"""
        return self._controller_type in ROOM_TO_ROOM_FAN_CONTROLLER_TYPES

    @property
    def is_airtap(self) -> bool:
        """Returns true if this device is an AIRTAP register fan rather than a controller with ports"""
        return self._is_airtap

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
            case ControllerType.UIS_ROOM_TO_ROOM_FAN:
                return "Room to Room Fan (AC-TWT6)"
            case ControllerType.AIRTAP_AI:
                return "AIRTAP AI Register Booster Fan"
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
                    model="UIS Controller Sensor Probe (AC-SPC24)",
                )
            case SensorType.CO2 | SensorType.LIGHT:
                return DeviceInfo(
                    identifiers={
                        (DOMAIN, f"{controller.controller_id}_{sensor_port}_cos3")
                    },
                    name=f"{controller.controller_name} CO2 + Light Sensor",
                    manufacturer=MANUFACTURER,
                    model="UIS CO2 + Light Sensor (AC-COS3)",
                )
            case SensorType.WATER:
                return DeviceInfo(
                    identifiers={
                        (DOMAIN, f"{controller.controller_id}_{sensor_port}_wds3")
                    },
                    name=f"{controller.controller_name} Water Sensor",
                    manufacturer=MANUFACTURER,
                    model="UIS Water Sensor (AC-WDS3)",
                )
            case SensorType.SOIL:
                return DeviceInfo(
                    identifiers={
                        (DOMAIN, f"{controller.controller_id}_{sensor_port}_sls3")
                    },
                    name=f"{controller.controller_name} Soil Sensor",
                    manufacturer=MANUFACTURER,
                    model="UIS Soil Sensor (AC-SLS3)",
                )
            case (
                SensorType.HYDRO_PH
                | SensorType.HYDRO_EC_US
                | SensorType.HYDRO_EC_MS
                | SensorType.HYDRO_TDS_PPM
                | SensorType.HYDRO_TDS_PPT
                | SensorType.HYDRO_WATER_TEMPERATURE_F
                | SensorType.HYDRO_WATER_TEMPERATURE_C
            ):
                return DeviceInfo(
                    identifiers={
                        (DOMAIN, f"{controller.controller_id}_{sensor_port}_hds3")
                    },
                    name=f"{controller.controller_name} Hydro Sensor",
                    manufacturer=MANUFACTURER,
                    model="UIS Hydro Sensor (AC-HDS3)",
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

        if self._device_port == 0:
            # Port 0 only exists for portless fans (AIRTAP, room-to-room). The fan is a single physical
            # unit: its controls and its controller-level sensors belong on one device.
            self._device_info = controller.device_info
            return

        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{controller.controller_id}_{self._device_port}")},
            name=f"{controller.controller_name} {self.device_name}",
            manufacturer=MANUFACTURER,
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


@dataclass
class ACInfinityData:
    """POPO encapsulating the cached properties/settings tracked by ACInfinityService"""

    controller_properties: dict[str, Any] = field(default_factory=dict)
    sensor_properties: dict[tuple[str, int, int], Any] = field(default_factory=dict)
    device_properties: dict[tuple[str, int], Any] = field(default_factory=dict)
    device_controls: dict[tuple[str, int], Any] = field(default_factory=dict)
    device_settings: dict[tuple[str, int], Any] = field(default_factory=dict)


class ACInfinityService:
    """Service layer object responsible for initializing and updating values from the AC Infinity API"""

    MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)

    def __init__(
        self, client: ACInfinityClient, data: ACInfinityData
    ) -> None:
        """
        Args:
            client: The http client to use to make requests to the AC Infinity API
        """
        self.client = client
        self.data = data
        self._update_lock = asyncio.Lock()
        self._controller_locks: dict[str, asyncio.Lock] = {}

    def _controller_lock(self, controller_id: str | int) -> asyncio.Lock:
        """Serializes reads and writes for one controller, so a refresh never races a write's optimistic cache
        update.  Each controller has its own lock so accounts with many controllers refresh them in parallel."""
        return self._controller_locks.setdefault(str(controller_id), asyncio.Lock())

    def get_device_ids(self) -> list[str]:
        """
        returns a list of devices associated with the account
        """
        return list(self.data.controller_properties.keys())

    def get_device_ports(self, controller_id: str | int) -> list[int]:
        """
        returns the port indexes known for a controller (0 for a portless fan, 1..n for controllers)
        """
        controller_json = self.data.controller_properties.get(str(controller_id))
        if controller_json is None:
            return []
        return sorted(port_json[DevicePropertyKey.PORT] for port_json in ACInfinityController.get_port_jsons(controller_json))

    def get_controller_property_exists(
        self, controller_id: str | int, property_key: str
    ) -> bool:
        """returns if a given property exists on a given controller.

        Args:
            controller_id: the device id of the controller
            property_key: the json field name for the data being retrieved
        """
        normalized_id = str(controller_id)
        if normalized_id in self.data.controller_properties:
            result = self.data.controller_properties[normalized_id]
            if property_key in result:
                return True
            return property_key in result[ControllerPropertyKey.DEVICE_INFO]

        return False

    def get_controller_property(
        self, controller_id: str | int, property_key: str, default_value=None
    ) -> Any:
        """gets a property value for a given controller, if both the property and controller exist.

        Args:
            controller_id: the device id of the controller
            property_key: the json field name for the data being retrieved
            default_value: the value to return if the controller or property doesn't exist
        """
        normalized_id = str(controller_id)
        if normalized_id in self.data.controller_properties:
            result = self.data.controller_properties[normalized_id]
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
            normalized_id in self.data.sensor_properties
            and property_key in self.data.sensor_properties[normalized_id]
        )

    def get_sensor_property(
        self,
        controller_id: str | int,
        sensor_port: int,
        sensor_type: int,
        property_key: str,
        default_value=None,
    ) -> Any:
        """gets a property value for a given sensor on a controller, if the property, controller, access port, and sensor all exist.

        Args:
            controller_id:  the device id of the controller
            sensor_port: the index of the sensor port on the controller
            sensor_type: the type of sensor
            property_key: the json filed name for the data being retrieved
            default_value: the default value to return if the controller, port, or property doesn't exist
        """
        normalized_id = (str(controller_id), sensor_port, sensor_type)
        if normalized_id in self.data.sensor_properties:
            found = self.data.sensor_properties[normalized_id]
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
            normalized_id in self.data.device_properties
            and property_key in self.data.device_properties[normalized_id]
        )

    def get_device_property(
        self,
        controller_id: str | int,
        device_port: int,
        property_key: str,
        default_value=None,
    ) -> Any:
        """gets a property value for a given port on a controller, if the property, controller and port all exist.

        Args:
            controller_id:  the device id of the controller
            device_port: the index of the port on the controller
            property_key: the json filed name for the data being retrieved
            default_value: the default value to return if the controller, port, or property doesn't exist
        """
        normalized_id = (str(controller_id), device_port)
        if normalized_id in self.data.device_properties:
            found = self.data.device_properties[normalized_id]
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
    ) -> Any:
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
        return normalized_id in self.data.device_settings and setting_key in self.data.device_settings[normalized_id]

    def get_device_setting(
        self,
        controller_id: str | int,
        device_port: int,
        setting_key: str,
        default_value=None,
    ) -> Any:
        """gets a property value for a given device, if both the setting and device exist.

        Args:
            controller_id: the device id of the controller
            device_port: the port index of the device
            setting_key: the json field name for the data being retrieved
            default_value: the value to return if the controller or property doesn't exist
        """
        normalized_id = str(controller_id)
        if (normalized_id, device_port) in self.data.device_settings:
            result = self.data.device_settings[(normalized_id, device_port)]
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
        if normalized_id in self.data.device_controls:
            found = self.data.device_controls[normalized_id]
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
    ) -> Any:
        """gets the current set value for a given device setting

        Args:
            controller_id: the device id of the controller
            device_port: the index of the port on the controller
            setting_key: the setting to pull the value of
            default_value: the default value to return if the controller, port, or setting doesn't exist
        """
        normalized_id = (str(controller_id), device_port)
        if normalized_id in self.data.device_controls:
            result = self.data.device_controls[normalized_id]
            if setting_key in result:
                value = result[setting_key]
                return value if value is not None else default_value
            elif setting_key in result[DeviceControlKey.DEV_SETTING]:
                value = result[DeviceControlKey.DEV_SETTING][setting_key]
                return value if value is not None else default_value

        return default_value

    async def _execute_with_retry[T](
        self,
        action: Callable[[], Awaitable[T]],
        operation_name: str,
        max_attempts: int = 4,
    ) -> T:
        """Executes an async action, retrying transient API failures with exponential backoff.

        A Polly-style retry policy: retryable network/API errors are retried with
        increasing delay between attempts, while auth failures and unexpected errors
        are raised immediately without retrying.

        Args:
            action: the operation to invoke, and retry if it fails
            operation_name: human-readable description of the operation, used in log messages
            max_attempts: the maximum number of retry attempts after the initial call
        """
        try_count = 0
        while True:
            try:
                return await action()
            except (
                ACInfinityClientCannotConnect,
                ACInfinityClientRequestFailed,
                aiohttp.ClientError,
                asyncio.TimeoutError,
            ) as ex:
                if try_count < max_attempts:
                    try_count += 1
                    delay = 2 ** (try_count - 1)  # exponential backoff: 1s, 2s, 4s, 8s...
                    _LOGGER.warning(
                        "Unable to %s. Retry attempt %s/%s in %ss", operation_name, try_count, max_attempts, delay
                    )
                    await asyncio.sleep(delay)
                else:
                    _LOGGER.error(ACINFINITY_API_ERROR, exc_info=ex)
                    raise
            except ACInfinityClientInvalidAuth as ex:
                _LOGGER.error("Unable to %s: Authentication failed", operation_name, exc_info=ex)
                raise
            except Exception as ex:
                _LOGGER.error("Unable to %s: Unexpected error", operation_name, exc_info=ex)
                raise

    async def refresh_controllers(self) -> None:
        """Refreshes controller/sensor/port properties from the AC Infinity API.

        Used when data is needed before the device coordinators are running (e.g. setup,
        config/options flow), and by ACInfinityDeviceListCoordinator on its polling interval.
        Mode settings/controls are owned by ACInfinityDeviceCoordinator and are not refreshed here.
        """
        async def _refresh() -> None:
            if not self.client.is_logged_in():
                await self.client.login()

            all_devices_json = await self.client.get_account_controllers()
            for controller_properties_json in all_devices_json:
                # cache keys are always the string id; every getter looks values up by str(controller_id)
                controller_id = str(controller_properties_json[ControllerPropertyKey.DEVICE_ID])

                # set controller properties; readings for temp, vpd, humidity, etc...
                self.data.controller_properties[controller_id] = controller_properties_json

                # Room-to-room fans (e.g. AC-TWT6) have no ports, so the loop below never runs for
                # them. Synthesize the port 0 device properties here; _device_properties gates entity
                # availability via the ONLINE property check, so without it every control is greyed out.
                if controller_properties_json.get(ControllerPropertyKey.DEVICE_TYPE) in ROOM_TO_ROOM_FAN_CONTROLLER_TYPES:
                    # State/speed/remaining time for this device come from its mode settings (see
                    # refresh_device_settings), so keep whatever that last stored and only update ONLINE.
                    synthetic_properties = self.data.device_properties.setdefault(
                        (controller_id, 0), ACInfinityController.get_port_jsons(controller_properties_json)[0]
                    )
                    synthetic_properties[DevicePropertyKey.ONLINE] = controller_properties_json[ControllerPropertyKey.ONLINE]

                # controller AI will have a sensor array.
                if ControllerPropertyKey.SENSORS in controller_properties_json[ControllerPropertyKey.DEVICE_INFO]:
                    sensors = controller_properties_json[ControllerPropertyKey.DEVICE_INFO][ControllerPropertyKey.SENSORS] or []
                    for sensor_properties_json in sensors:
                        access_port_index = sensor_properties_json[SensorPropertyKey.ACCESS_PORT]
                        sensor_type = sensor_properties_json[SensorPropertyKey.SENSOR_TYPE]

                        # set sensor properties; sensor value, unit, and display precision
                        self.data.sensor_properties[(controller_id, access_port_index, sensor_type)] = sensor_properties_json

                if controller_properties_json.get(ControllerPropertyKey.DEVICE_TYPE) in ROOM_TO_ROOM_FAN_CONTROLLER_TYPES:
                    continue

                for device_properties_json in ACInfinityController.get_port_jsons(controller_properties_json):
                    device_port = device_properties_json[DevicePropertyKey.PORT]

                    # set port properties; current power and remaining time until a mode switch
                    self.data.device_properties[(controller_id, device_port)] = device_properties_json

        async with self._update_lock:
            await self._execute_with_retry(_refresh, "refresh controllers")

    async def refresh_device_settings(self, controller_id: str, port_indexes: Iterable[int]) -> None:
        """Refreshes mode settings/controls for the given ports on a controller from the AC Infinity API.

        Used by ACInfinityDeviceCoordinator on its polling interval. Each port is refreshed independently
        so a failure retrieving one port's settings does not delay or prevent the others from updating.
        Falls back to every known port on the controller if no ports are given (e.g. before any entity
        has subscribed to the coordinator yet).
        """
        if not (port_indexes := set(port_indexes)):
            # port 0 holds controller-level settings (or the fan itself on portless fans)
            port_indexes = {0, *self.get_device_ports(controller_id)}

        port_indexes = list(port_indexes)

        # AI controllers read and write settings through the mode endpoint, while standard
        # controllers use the advanced settings endpoint (mirrors update_device_setting).
        # Portless fans (AIRTAP, room-to-room) are also written through the mode endpoint.
        controller_properties = self.data.controller_properties.get(str(controller_id))
        controller = ACInfinityController(controller_properties) if controller_properties is not None else None
        settings_from_mode_endpoint = controller is not None and (
            controller.is_ai_controller or controller.is_airtap or controller.is_room_to_room_fan
        )

        async def _refresh_port(port_index: int) -> None:
            controls = await self._execute_with_retry(
                lambda: self.client.get_device_mode_settings(controller_id, port_index),
                f"refresh device controls for controller {controller_id} port {port_index}",
            )
            if settings_from_mode_endpoint:
                settings = controls[DeviceControlKey.DEV_SETTING]
            else:
                settings = await self._execute_with_retry(
                    lambda: self.client.get_device_settings(controller_id, port_index),
                    f"refresh device settings for controller {controller_id} port {port_index}",
                )
            self.data.device_controls[(controller_id, port_index)] = controls
            self.data.device_settings[(controller_id, port_index)] = settings

            # Room-to-room fans have no ports; their on/off state, current speed and timer countdown only
            # exist in the mode settings, so mirror them into the synthetic port 0 device properties.
            if (
                port_index == 0
                and self.get_controller_property(controller_id, ControllerPropertyKey.DEVICE_TYPE) in ROOM_TO_ROOM_FAN_CONTROLLER_TYPES
            ):
                dev_setting = controls.get(DeviceControlKey.DEV_SETTING) or {}

                def _value(key: str, default: int = 0) -> int:
                    value = controls.get(key)
                    if value is None:
                        value = dev_setting.get(key)
                    return default if value is None else value

                properties = self.data.device_properties.setdefault((controller_id, 0), {DevicePropertyKey.PORT: 0})
                properties[DevicePropertyKey.SPEAK] = _value(DevicePropertyKey.SPEAK)
                # State reflects whether the fan is actually moving, not just powered on (idle in AI/Temp modes)
                properties[DevicePropertyKey.STATE] = 1 if _value(DeviceControlKey.POWER_STATE) and properties[DevicePropertyKey.SPEAK] > 0 else 0
                properties[DevicePropertyKey.REMAINING_TIME] = _value(DeviceControlKey.SURPLUS)

        async with self._controller_lock(controller_id):
            results = await asyncio.gather(
                *(_refresh_port(port_index) for port_index in port_indexes),
                return_exceptions=True,
            )

        uncached_failure: BaseException | None = None
        for port_index, result in zip(port_indexes, results):
            if isinstance(result, BaseException):
                _LOGGER.error("Error refreshing device settings for controller %s port %s: %s", controller_id, port_index, result)
                if (controller_id, port_index) not in self.data.device_controls:
                    uncached_failure = uncached_failure or result

        # a port that has never been retrieved has no data for entities to be built from (e.g. on startup),
        # so fail the refresh rather than letting its settings/controls be silently skipped as unsuitable.
        if uncached_failure is not None:
            raise uncached_failure

    def get_all_controller_properties(self) -> list[ACInfinityController]:
        """gets device metadata, such as ids, labels, macaddr, etc... that are not expected to change"""
        if self.data.controller_properties is None:
            return []

        return [ACInfinityController(device) for device in self.data.controller_properties.values()]

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
        self, controller: ACInfinityController, key_values: dict[str, Any]
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller: controller to update
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        if controller.is_ai_controller:
            raise NotImplementedError("AI controllers do not support updating controller settings: %s", key_values)
        elif controller.is_airtap:
            raise NotImplementedError("AIRTAP fans do not support updating controller settings: %s", key_values)
        else:
            await self.__update_advanced_settings(controller.controller_id, 0, controller.controller_name, key_values)

    async def update_device_setting(
        self,
        device: ACInfinityDevice,
        setting_key: str,
        new_value: int | str,
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
        key_values: dict[str, Any],
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            device: the device
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        if device.controller.is_ai_controller:
            await self.__update_ai_control_and_settings(device.controller.controller_id, device.device_port, key_values)
        elif device.controller.is_airtap:
            raise NotImplementedError("AIRTAP fans do not support updating device settings: %s", key_values)
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
        key_values: dict[str, Any],
    ):
        if device.controller.is_ai_controller:
            await self.__update_ai_control_and_settings(device.controller.controller_id, device.device_port, key_values)
        elif device.controller.is_room_to_room_fan:
            if ROOM_TO_ROOM_FAN_DISPLAY_SETTING_TRIGGER_KEYS.intersection(key_values):
                controller_id = device.controller.controller_id
                await self.__update_room_to_room_fan_display_setting(
                    controller_id,
                    device.device_port,
                    self.get_controller_property(controller_id, ControllerPropertyKey.DEVICE_NAME, ""),
                    self.get_controller_property(controller_id, ControllerPropertyKey.INSIDE_ROOM_NAME, ""),
                    self.get_controller_property(controller_id, ControllerPropertyKey.OUTSIDE_ROOM_NAME, ""),
                    key_values,
                )
            else:
                await self.__update_room_to_room_fan_controls(device.controller.controller_id, device.device_port, key_values)
        elif device.controller.is_airtap:
            await self.__update_airtap_controls(device.controller.controller_id, key_values)
        else:
            await self.__update_device_controls(device.controller.controller_id, device.device_port, key_values)

    async def __update_device_controls(
        self,
        controller_id: str | int,
        device_port: int,
        key_values: dict[str, Any],
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller_id: the device id of the controller
            device_port: the index of the port on the controller
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        async with self._controller_lock(controller_id):
            await self._execute_with_retry(
                lambda: self.client.update_device_controls(controller_id, device_port, key_values),
                "update device controls",
            )
            self.__cache_updated_values(self.data.device_controls, controller_id, device_port, key_values)

    async def __update_advanced_settings(
        self,
        controller_id: str | int,
        device_port: int,
        device_name: str,
        key_values: dict[str, Any],
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller_id: The device id of the controller to update
            device_port: 0 for controller settings, or the port number for port settings
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        async with self._controller_lock(controller_id):
            await self._execute_with_retry(
                lambda: self.client.update_device_settings(controller_id, device_port, device_name, key_values),
                "update advanced controller settings",
            )
            self.__cache_updated_values(self.data.device_settings, controller_id, device_port, key_values)

    async def __update_ai_control_and_settings(
        self,
        controller_id: str | int,
        device_port: int,
        key_values: dict[str, Any],
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller_id: the device id of the controller
            device_port: the index of the port on the controller
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        async with self._controller_lock(controller_id):
            await self._execute_with_retry(
                lambda: self.client.update_ai_device_control_and_settings(controller_id, device_port, key_values),
                "update ai device controls and settings",
            )
            self.__cache_updated_values(self.data.device_controls, controller_id, device_port, key_values)

            # AI controllers combine controls and settings in one payload; only mirror keys that
            # already belong to the cached settings dict so control-only keys aren't misclassified.
            settings = self.data.device_settings.get((str(controller_id), device_port), {})
            setting_values = {key: value for key, value in key_values.items() if key in settings}
            if setting_values:
                self.__cache_updated_values(self.data.device_settings, controller_id, device_port, setting_values)

    @staticmethod
    def __cache_updated_values(
        cache: dict[tuple[str, int], Any],
        controller_id: str | int,
        device_port: int,
        key_values: dict[str, Any],
    ) -> None:
        """Optimistically applies a just-written value to the cache so entities redraw with the new
        value immediately, rather than a stale value from a refresh that raced the API's write."""
        normalized_id = (str(controller_id), device_port)
        cache[normalized_id] = {**cache.get(normalized_id, {}), **key_values}

    async def __update_room_to_room_fan_controls(
        self,
        controller_id: str | int,
        device_port: int,
        key_values: dict[str, Any],
    ):
        """Update the values of a set of settings via the AC Infinity API

        Args:
            controller_id: the device id of the controller
            device_port: the index of the port on the controller (always 0)
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        async with self._controller_lock(controller_id):
            await self._execute_with_retry(
                lambda: self.client.update_room_to_room_fan_control(controller_id, device_port, key_values),
                "update room-to-room fan controls",
            )
            self.__cache_updated_values(self.data.device_controls, controller_id, device_port, key_values)

    async def __update_room_to_room_fan_display_setting(
        self,
        controller_id: str | int,
        device_port: int,
        dev_name: str,
        inside_room_name: str,
        outside_room_name: str,
        key_values: dict[str, Any],
    ):
        """Update display/panel settings (backlight, keytone, brightness) via the AC
        Infinity API. These use a different request shape than other room-to-room fan
        controls - see ACInfinityClient.update_room_to_room_fan_display_setting.

        Args:
            controller_id: the device id of the controller
            device_port: the index of the port on the controller (always 0)
            dev_name: the controller's display name, as configured in the app
            inside_room_name: the "inside" zone's room name, as configured in the app
            outside_room_name: the "outside" zone's room name, as configured in the app
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        async with self._controller_lock(controller_id):
            await self._execute_with_retry(
                lambda: self.client.update_room_to_room_fan_display_setting(
                    controller_id, device_port, dev_name, inside_room_name, outside_room_name, key_values
                ),
                "update room-to-room fan display setting",
            )
            self.__cache_updated_values(self.data.device_controls, controller_id, device_port, key_values)

    async def __update_airtap_controls(
        self,
        controller_id: str | int,
        key_values: dict[str, Any],
    ):
        """Update the mode and/or speeds of an AIRTAP register fan via the AC Infinity API

        Args:
            controller_id: the device id of the fan
            key_values: a list of key/value pairs to update, as a tuple of (setting_key, new_value)
        """
        async with self._controller_lock(controller_id):
            await self._execute_with_retry(
                lambda: self.client.update_airtap_controls(controller_id, key_values),
                "update AIRTAP controls",
            )
            self.__cache_updated_values(self.data.device_controls, controller_id, 0, key_values)

    async def close(self) -> None:
        """Close the client session when done"""
        if self.client:
            await self.client.close()


class ACInfinityDeviceListCoordinator(DataUpdateCoordinator):

    def __init__(
            self, 
            hass: HomeAssistant,
            entry: ConfigEntry,
            service: ACInfinityService,
            polling_interval: int,
        ):

        self.service = service

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=polling_interval),
        )

    async def _async_update_data(self):
        """Refresh the device list from the AC Infinity API"""
        _LOGGER.debug("Refreshing global device list.")

        try:
            await self.service.refresh_controllers()
        except Exception as e:
            _LOGGER.error("Error refreshing global device list: %s", e)
            raise UpdateFailed from e


class ACInfinityDeviceCoordinator(DataUpdateCoordinator):
    """Polls mode settings/controls for a single controller's ports.

    Listeners subscribe with a port index as their context (0 for controller-level
    settings). Only ports with an active listener are refreshed, falling back to
    every known port on the controller before any entity has subscribed yet.
    """

    _controller_id: str

    def __init__(
            self,
            controller_id: str,
            hass: HomeAssistant,
            entry: ConfigEntry,
            service: ACInfinityService,
            polling_interval: int,
        ):

        self._controller_id = controller_id
        self.service = service

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=polling_interval),
        )

    async def _async_update_data(self):
        try:
            # port 0 carries controller level settings other ports depend on (e.g. the temperature unit),
            # so it is polled whenever any port is
            contexts = set(self.async_contexts())
            await self.service.refresh_device_settings(self._controller_id, contexts | {0} if contexts else contexts)
        except Exception as e:
            _LOGGER.error("Error refreshing device settings for controller %s: %s", self._controller_id, e)
            raise UpdateFailed from e


@dataclass
class ACInfinityEntryData:
    """Bundle of coordinators stored in hass.data for a config entry"""

    service: ACInfinityService
    """Shared service facade for reading/writing cached AC Infinity data"""
    list_coordinator: ACInfinityDeviceListCoordinator
    """Single coordinator responsible for polling the account's controller/sensor/port list"""
    device_coordinators: dict[str, ACInfinityDeviceCoordinator]
    """One coordinator per controller_id responsible for polling that controller's mode settings/controls.
    Listeners use the port index (0 for controller-level settings) as their subscription context."""
    excluded_unique_ids: set[tuple[str, str]] = field(default_factory=set)
    """(platform, unique id) of entities the user excluded (entity filters or per-device options); purged from the
    registry.  The platform is part of the key because unique ids are only unique within a platform.
    Entities merely missing from the API's data this time are deliberately not tracked, so they are never purged."""


class ACInfinityEntity(CoordinatorEntity[ACInfinityDeviceListCoordinator], ABC):
    _attr_has_entity_name = True
    coordinator: ACInfinityDeviceListCoordinator
    translation_key: str

    def __init__(
        self,
        platform: str,
        data_key: str,
        list_coordinator: ACInfinityDeviceListCoordinator,
        device_coordinator: ACInfinityDeviceCoordinator | None = None,
        device_context: int | None = None,
    ):
        super().__init__(list_coordinator)
        self._platform_name = platform
        self._data_key = data_key
        self._device_coordinator = device_coordinator
        self._device_context = device_context

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._device_coordinator is not None:
            self.async_on_remove(
                self._device_coordinator.async_add_listener(
                    self._handle_coordinator_update, context=self._device_context
                )
            )

    def __repr__(self):
        return f"<ACInfinityEntity unique_id={self.unique_id}>"

    @property
    def data_key(self) -> str:
        """Returns the underlying ac_infinity api data key used to track the data"""
        return self._data_key

    @property
    def device_coordinator(self) -> ACInfinityDeviceCoordinator | None:
        """Returns the per-port coordinator responsible for mode settings/controls, if any."""
        return self._device_coordinator

    @property
    def service(self) -> ACInfinityService:
        """Returns the underlying ac_infinity api object from the assigned coordinator"""
        return self.coordinator.service

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

    @property
    def available(self) -> bool:
        """Returns true only if both the list coordinator and, if assigned, the device coordinator last refreshed successfully"""
        if self._device_coordinator is not None and not self._device_coordinator.last_update_success:
            return False
        return super().available

    def _resolve_via_device_id(self, identifier: tuple[str, str]) -> str | None:
        """Resolves the HA device registry id for a via_device identifier, if already registered"""
        if self.hass is None or self.coordinator.config_entry is None:
            return None

        device = dr.async_get(self.hass).async_get_device_by_identifier(
            identifier, self.coordinator.config_entry.entry_id
        )
        return device.id if device is not None else None

    def notify_device_update(self) -> None:
        """Writes this entity's state, and redraws every entity sharing this device's per-port
        coordinator context from the cache (e.g. after a write updates AT_TYPE, so entities whose
        availability depends on the new mode reflect it immediately instead of waiting for the next
        poll). Does not touch the API."""
        self.async_write_ha_state()
        if self._device_coordinator is not None:
            self._device_coordinator.async_update_listeners()


class ACInfinityControllerEntity(ACInfinityEntity):
    def __init__(
        self,
        controller: ACInfinityController,
        enabled_fn: Callable[[ConfigEntry, str, str], bool],
        suitable_fn: Callable[[ACInfinityEntity, ACInfinityController], bool],
        data_key: str,
        platform: str,
        list_coordinator: ACInfinityDeviceListCoordinator,
        device_coordinator: ACInfinityDeviceCoordinator | None = None,
    ):
        # controller-level settings are always tracked under port index 0
        super().__init__(platform, data_key, list_coordinator, device_coordinator, device_context=0)
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
        if self._controller.is_airtap and self.data_key not in AIRTAP_CONTROLLER_KEYS:
            return False
        return self._suitable_fn(self, self.controller)


class ACInfinitySensorEntity(ACInfinityEntity):
    def __init__(
        self,
        sensor: ACInfinitySensor,
        enabled_fn: Callable[[ConfigEntry, str, str], bool],
        suitable_fn: Callable[[ACInfinityEntity, ACInfinitySensor], bool],
        data_key: str,
        platform: str,
        list_coordinator: ACInfinityDeviceListCoordinator,
    ):
        super().__init__(platform, data_key, list_coordinator)
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
        device_info = self._sensor.device_info
        # controller-level sensors reuse the controller's own device_info; no via_device needed
        if device_info is not self._sensor.controller.device_info:
            via_device_id = self._resolve_via_device_id(self._sensor.controller.identifier)
            if via_device_id is not None:
                device_info = DeviceInfo(**device_info)
                device_info["via_device_id"] = via_device_id
        return device_info

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
        device: ACInfinityDevice,
        enabled_fn: Callable[[ConfigEntry, str, str], bool],
        suitable_fn: Callable[[ACInfinityEntity, ACInfinityDevice], bool],
        at_type_fn: Callable[[int], bool] | None,
        data_key: str,
        platform: str,
        list_coordinator: ACInfinityDeviceListCoordinator,
        device_coordinator: ACInfinityDeviceCoordinator | None = None,
    ):
        super().__init__(platform, data_key, list_coordinator, device_coordinator, device_context=device.device_port)
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
        device_info = self._device.device_info
        if device_info is self._device.controller.device_info:
            return device_info  # device shares the controller's own device (room-to-room fans)
        via_device_id = self._resolve_via_device_id(self._device.controller.identifier)
        if via_device_id is not None:
            device_info = DeviceInfo(**device_info)
            device_info["via_device_id"] = via_device_id
        return device_info

    @property
    def device_port(self) -> ACInfinityDevice:
        return self._device

    def is_enabled(self, entry: ConfigEntry) -> bool:
        return self._enabled_fn(entry, str(self._device.controller.controller_id), f"port_{self._device.device_port}")

    @property
    def is_suitable(self) -> bool:
        if self._device.controller.is_airtap and self.data_key not in AIRTAP_DEVICE_KEYS:
            return False
        return self._suitable_fn(self, self.device_port)

    @property
    def available(self) -> bool:
        """Returns true if the device is online and, if provided, the active mode matches the at_type filter"""
        active_at_type = self.service.get_device_control(
            self._device.controller.controller_id,
            self.device_port.device_port,
            DeviceControlKey.AT_TYPE
        )
        return super().available and self.service.get_device_property(
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
    def __init__(self, config: ConfigEntry, excluded_unique_ids: set[tuple[str, str]] | None = None):
        super().__init__()
        self._config_entry = config
        self._excluded_unique_ids = excluded_unique_ids

    def __exclude(self, entity: ACInfinityEntity):
        if self._excluded_unique_ids is not None:
            self._excluded_unique_ids.add((str(entity.platform_name), entity.unique_id))

    def append_if_suitable(self, entity: ACInfinityEntity):

        if is_excluded_by_filters(self._config_entry, entity):
            self.__exclude(entity)
            _LOGGER.debug(
                'Ignoring excluded entity "%s" (%s) for platform "%s". (Excluded by user)',
                entity.unique_id,
                entity.translation_key,
                entity.platform_name,
            )
        elif entity.is_enabled(self._config_entry):
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
            self.__exclude(entity)
            _LOGGER.debug(
                'Ignoring disabled entity "%s" (%s) for platform "%s". (Disabled by user)',
                entity.unique_id,
                entity.translation_key,
                entity.platform_name,
            )


ALL_AT_TYPES = frozenset(
    value for name, value in vars(AtType).items() if not name.startswith("_") and isinstance(value, int)
)


def is_excluded_by_filters(entry: ConfigEntry, entity: ACInfinityEntity) -> bool:
    """True if the user excluded this entity integration-wide, either by its type (e.g. every "Cycle Duration On")
    or because every mode it applies to was excluded (e.g. all Schedule mode entities)."""
    excluded_types = entry.data.get(ConfigurationKey.EXCLUDED_ENTITY_TYPES) or []
    if f"{entity.platform_name}.{entity.translation_key}" in excluded_types:
        return True

    excluded_modes = {int(mode) for mode in entry.data.get(ConfigurationKey.EXCLUDED_MODES) or []}
    at_type_fn = getattr(entity, "_at_type_fn", None)
    if not excluded_modes or at_type_fn is None:
        return False

    # room-to-room fans reuse atType with unrelated mode numbers
    if isinstance(entity, ACInfinityDeviceEntity) and entity.device_port.controller.is_room_to_room_fan:
        return False

    # entities shown in every mode are not mode specific, so a mode filter never removes them
    applicable_modes = {mode for mode in ALL_AT_TYPES if at_type_fn(mode)}
    return applicable_modes != ALL_AT_TYPES and applicable_modes <= excluded_modes


def get_entity_config_value(entry: ConfigEntry, device_id: str, entity_config_key: str) -> str:
    """The entity configuration chosen for a device / port, or the setup default (sensors only) when the device or
    port was added to the account after the integration was configured and has no saved choice yet."""
    return (
        entry.data.get(ConfigurationKey.ENTITIES, {})
        .get(device_id, {})
        .get(entity_config_key, EntityConfigValue.SENSORS_ONLY)
    )


def enabled_fn_sensor(entry: ConfigEntry, device_id: str, entity_config_key: str) -> bool:
    return get_entity_config_value(entry, device_id, entity_config_key) != EntityConfigValue.DISABLE


def enabled_fn_control(entry: ConfigEntry, device_id: str, entity_config_key: str) -> bool:
    setting = get_entity_config_value(entry, device_id, entity_config_key)
    return setting == EntityConfigValue.ALL or setting == EntityConfigValue.SENSORS_AND_CONTROLS


def enabled_fn_setting(entry: ConfigEntry, device_id: str, entity_config_key: str) -> bool:
    setting = get_entity_config_value(entry, device_id, entity_config_key)
    return setting == EntityConfigValue.ALL or setting == EntityConfigValue.SENSORS_AND_SETTINGS

