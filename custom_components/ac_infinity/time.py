import datetime
import logging
from dataclasses import dataclass
from datetime import time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from custom_components.ac_infinity.const import (
    AtType, DOMAIN, SCHEDULE_DISABLED_VALUE, DeviceControlKey,
)
from custom_components.ac_infinity.core import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntities,
    ACInfinityEntity,
    ACInfinityDevice,
    ACInfinityDeviceEntity,
    ACInfinityDeviceReadWriteMixin, enabled_fn_control,
)

_LOGGER = logging.getLogger(__name__)


def __get_time_from_total_minutes(total_minutes: int) -> time | None:
    """UIS stores a schedule value as minutes from midnight. A value of 0 is midnight.
    Both 65535 and None could represent a value of disabled
    """
    if total_minutes is not None and total_minutes // 60 <= 23:
        return datetime.time(hour=total_minutes // 60, minute=total_minutes % 60)

    return None


def __get_total_minutes_from_time(source_time: time):
    """UIS stores a schedule value as minutes from midnight. Midnight will result in a value of 0.
    If time is None, 65535 will be returned as it represents a value of disabled.
    """
    return (
        SCHEDULE_DISABLED_VALUE
        if source_time is None
        else (source_time.hour * 60) + source_time.minute
    )


@dataclass(frozen=True)
class ACInfinityTimeEntityDescription(TimeEntityDescription):
    """Describes ACInfinity Time Entities."""

    key: str
    icon: str | None
    translation_key: str | None


@dataclass(frozen=True)
class ACInfinityDeviceTimeEntityDescription(
    ACInfinityTimeEntityDescription, ACInfinityDeviceReadWriteMixin
):
    """Describes ACInfinity Time Entities."""


def __suitable_fn_device_control_default(entity: ACInfinityEntity, device: ACInfinityDevice):
    return entity.ac_infinity.get_device_control_exists(
        device.controller.controller_id, device.device_port, entity.data_key
    )


def __get_value_fn_time(entity: ACInfinityEntity, device: ACInfinityDevice):
    return __get_time_from_total_minutes(
        entity.ac_infinity.get_device_control(
            device.controller.controller_id,
            device.device_port,
            entity.data_key,
            None,
        )
    )


def __set_value_fn_time(entity: ACInfinityEntity, device: ACInfinityDevice, value: time):
    return entity.ac_infinity.update_device_control(
        device,
        entity.data_key,
        __get_total_minutes_from_time(value),
    )


DEVICE_DESCRIPTIONS: list[ACInfinityDeviceTimeEntityDescription] = [
    ACInfinityDeviceTimeEntityDescription(
        key=DeviceControlKey.SCHEDULED_START_TIME,
        icon=None,  # default
        translation_key="schedule_mode_on_time",
        suitable_fn=__suitable_fn_device_control_default,
        enabled_fn=enabled_fn_control,
        get_value_fn=__get_value_fn_time,
        set_value_fn=__set_value_fn_time,
        at_type=AtType.SCHEDULE,
    ),
    ACInfinityDeviceTimeEntityDescription(
        key=DeviceControlKey.SCHEDULED_END_TIME,
        icon=None,  # default
        translation_key="schedule_mode_off_time",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_time,
        set_value_fn=__set_value_fn_time,
        at_type=AtType.SCHEDULE,
    ),
]


class ACInfinityDeviceTimeEntity(ACInfinityDeviceEntity, TimeEntity):
    entity_description: ACInfinityDeviceTimeEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityDeviceTimeEntityDescription,
        device: ACInfinityDevice,
    ) -> None:
        super().__init__(
            coordinator, device, description.enabled_fn, description.suitable_fn, description.at_type, description.key, Platform.TIME
        )
        self.entity_description = description

    @property
    def native_value(self) -> time | None:
        return self.entity_description.get_value_fn(self, self.device_port)

    async def async_set_value(self, value: time) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "%s"', self.unique_id, value
        )
        await self.entity_description.set_value_fn(self, self.device_port, value)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback
) -> None:
    """Set up the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    controllers = coordinator.ac_infinity.get_all_controller_properties()

    entities = ACInfinityEntities(config)
    for controller in controllers:

        for device in controller.devices:
            for description in DEVICE_DESCRIPTIONS:
                entities.append_if_suitable(
                    ACInfinityDeviceTimeEntity(coordinator, description, device)
                )

    add_entities_callback(entities)
