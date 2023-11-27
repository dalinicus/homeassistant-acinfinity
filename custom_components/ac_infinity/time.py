import datetime
import logging
from dataclasses import dataclass
from datetime import time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityPortEntity,
    ACInfinityPortReadWriteMixin,
)
from custom_components.ac_infinity.ac_infinity import (
    ACInfinityPort,
)
from custom_components.ac_infinity.const import (
    DOMAIN,
    SCHEDULE_DISABLED_VALUE,
    SETTING_KEY_SCHEDULED_END_TIME,
    SETTING_KEY_SCHEDULED_START_TIME,
)

_LOGGER = logging.getLogger(__name__)


def __get_time_from_total_minutes(total_minutes: int) -> time | None:
    """UIS stores a schedule value as minutes from midnight. A value of 0 is midnight.
    Both 65535 and None could represent a value of disabled
    """
    if total_minutes is not None and total_minutes // 60 <= 23:
        return datetime.time(hour=total_minutes // 60, minute=total_minutes % 60)

    return None


def __get_total_minutes_from_time(time: time):
    """UIS stores a schedule value as minutes from midnight. Midnight will result in a value of 0.
    If time is None, 65535 will be returned as it represents a value of disabled.
    """
    return SCHEDULE_DISABLED_VALUE if time is None else (time.hour * 60) + time.minute


@dataclass
class ACInfinityPortTimeEntityDescription(
    TimeEntityDescription, ACInfinityPortReadWriteMixin
):
    """Describes ACInfinity Time Entities."""


PORT_DESCRIPTIONS: list[ACInfinityPortTimeEntityDescription] = [
    ACInfinityPortTimeEntityDescription(
        key=SETTING_KEY_SCHEDULED_START_TIME,
        icon=None,  # default
        translation_key="schedule_mode_on_time",
        get_value_fn=lambda ac_infinity, port: (
            __get_time_from_total_minutes(
                ac_infinity.get_device_port_setting(
                    port.parent_device_id,
                    port.port_id,
                    SETTING_KEY_SCHEDULED_START_TIME,
                )
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_SCHEDULED_START_TIME,
                __get_total_minutes_from_time(value),
            )
        ),
    ),
    ACInfinityPortTimeEntityDescription(
        key=SETTING_KEY_SCHEDULED_END_TIME,
        icon=None,  # default
        translation_key="schedule_mode_off_time",
        get_value_fn=lambda ac_infinity, port: (
            __get_time_from_total_minutes(
                ac_infinity.get_device_port_setting(
                    port.parent_device_id, port.port_id, SETTING_KEY_SCHEDULED_END_TIME
                )
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_SCHEDULED_END_TIME,
                __get_total_minutes_from_time(value),
            )
        ),
    ),
]


class ACInfinityPortTimeEntity(ACInfinityPortEntity, TimeEntity):
    entity_description: ACInfinityPortTimeEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityPortTimeEntityDescription,
        port: ACInfinityPort,
    ) -> None:
        super().__init__(coordinator, port, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> time | None:
        return self.entity_description.get_value_fn(self.ac_infinity, self.port)

    async def async_set_value(self, value: time) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "%s"', self.unique_id, value
        )
        await self.entity_description.set_value_fn(self.ac_infinity, self.port, value)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    devices = coordinator.ac_infinity.get_all_device_meta_data()

    entities = []
    for device in devices:
        for port in device.ports:
            for description in PORT_DESCRIPTIONS:
                entities.append(
                    ACInfinityPortTimeEntity(coordinator, description, port)
                )

    add_entities_callback(entities)
