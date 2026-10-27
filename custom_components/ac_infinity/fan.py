import logging
import math
from typing import Any

from homeassistant.components.fan import FanEntity
from homeassistant.components.fan.const import FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.util.percentage import percentage_to_ranged_value, ranged_value_to_percentage

from custom_components.ac_infinity.const import (
    DOMAIN,
    AdvancedSettingsKey,
    AtType,
    DeviceControlKey,
)
from custom_components.ac_infinity.core import (
    ACInfinityDevice,
    ACInfinityDeviceCoordinator,
    ACInfinityDeviceEntity,
    ACInfinityDeviceListCoordinator,
    ACInfinityEntities,
    ACInfinityEntity,
    ACInfinityEntryData,
    enabled_fn_control,
)

_LOGGER = logging.getLogger(__name__)

SPEED_RANGE = (1, 10)

# Ports whose configured device type is clearly not a fan get no fan entity.  Ports with no device type set
# (the app default) still get one, since most UIS devices are fans and the type is often left unset.
NON_FAN_LOAD_TYPES = {
    1, 2, 3, 4, 5, 8,  # Grow Light, Humidifier, Dehumidifier, Heater, AC, Water Pump
    128, 129, 130, 131, 132, 133, 136, 137, 138,  # AI: Outlet, Grow Light, ..., Pumps, CO2 Regulator
}


def _speed_key(device: ACInfinityDevice) -> str:
    # AI controllers keep the On mode level in onSelfSpead; everything else uses onSpead
    return DeviceControlKey.ON_SELF_SPEED if device.controller.is_ai_controller else DeviceControlKey.ON_SPEED


def _suitable_fn(entity: ACInfinityEntity, device: ACInfinityDevice) -> bool:
    controller = device.controller
    load_type = entity.service.get_device_setting(
        controller.controller_id, device.device_port, AdvancedSettingsKey.DEVICE_LOAD_TYPE, 0
    )
    return (
        not controller.is_room_to_room_fan
        and load_type not in NON_FAN_LOAD_TYPES
        and entity.service.get_device_control_exists(controller.controller_id, device.device_port, DeviceControlKey.AT_TYPE)
        and entity.service.get_device_control_exists(controller.controller_id, device.device_port, _speed_key(device))
    )


class ACInfinityDeviceFanEntity(ACInfinityDeviceEntity, FanEntity):
    """A port (or AIRTAP fan) as a fan: on/off switches between On and Off mode, speed is the On mode level."""

    _attr_translation_key = "fan"
    _attr_speed_count = SPEED_RANGE[1]
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        list_coordinator: ACInfinityDeviceListCoordinator,
        device_coordinator: ACInfinityDeviceCoordinator,
        device: ACInfinityDevice,
    ) -> None:
        super().__init__(
            device, enabled_fn_control, _suitable_fn, None, "fan", Platform.FAN, list_coordinator, device_coordinator
        )

    def __get_control(self, key: str):
        return self.service.get_device_control(self.device_port.controller.controller_id, self.device_port.device_port, key)

    @property
    def is_on(self) -> bool | None:
        at_type = self.__get_control(DeviceControlKey.AT_TYPE)
        return None if at_type is None else at_type != AtType.OFF

    @property
    def percentage(self) -> int | None:
        if not self.is_on:
            return 0
        speed = self.__get_control(_speed_key(self.device_port)) or 0
        return ranged_value_to_percentage(SPEED_RANGE, speed) if speed else 0

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any) -> None:
        key_values = {DeviceControlKey.AT_TYPE: AtType.ON}
        if percentage is not None:
            if percentage == 0:
                await self.async_turn_off()
                return
            key_values[_speed_key(self.device_port)] = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))

        _LOGGER.info('User requesting "%s" to turn on with %s', self.unique_id, key_values)
        await self.service.update_device_controls(self.device_port, key_values)
        self.notify_device_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        _LOGGER.info('User requesting "%s" to turn off', self.unique_id)
        await self.service.update_device_control(self.device_port, DeviceControlKey.AT_TYPE, AtType.OFF)
        self.notify_device_update()

    async def async_set_percentage(self, percentage: int) -> None:
        await self.async_turn_on(percentage=percentage)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback
) -> None:
    """Set up the AC Infinity Platform."""
    entry_data: ACInfinityEntryData = hass.data[DOMAIN][config.entry_id]

    entities = ACInfinityEntities(config)
    for controller in entry_data.service.get_all_controller_properties():
        device_coordinator = entry_data.device_coordinators[controller.controller_id]
        for device in controller.devices:
            entities.append_if_suitable(ACInfinityDeviceFanEntity(entry_data.list_coordinator, device_coordinator, device))

    add_entities_callback(entities)
