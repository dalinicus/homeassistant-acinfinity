import datetime
import logging
from dataclasses import dataclass
from datetime import time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from custom_components.ac_infinity.const import (
    DOMAIN,
    SCHEDULE_DISABLED_VALUE,
    ControllerType,
    PortControlKey,
)
from custom_components.ac_infinity.core import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntities,
    ACInfinityEntity,
    ACInfinityPort,
    ACInfinityPortEntity,
    ACInfinityPortReadWriteMixin,
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


@dataclass
class ACInfinityTimeEntityDescription(TimeEntityDescription):
    """Describes ACInfinity Time Entities."""

    key: str
    icon: str | None
    translation_key: str | None


@dataclass
class ACInfinityPortTimeEntityDescription(
    ACInfinityTimeEntityDescription, ACInfinityPortReadWriteMixin
):
    """Describes ACInfinity Time Entities."""


def __suitable_fn_port_control_default(entity: ACInfinityEntity, port: ACInfinityPort):
    return entity.ac_infinity.get_port_control_exists(
        port.controller.device_id, port.port_index, entity.entity_description.key
    )


def __get_value_fn_time(entity: ACInfinityEntity, port: ACInfinityPort):
    return __get_time_from_total_minutes(
        entity.ac_infinity.get_port_control(
            port.controller.device_id,
            port.port_index,
            entity.entity_description.key,
            None,
        )
    )


def __set_value_fn_time(entity: ACInfinityEntity, port: ACInfinityPort, value: time):
    return entity.ac_infinity.update_port_control(
        port.controller.device_id,
        port.port_index,
        entity.entity_description.key,
        __get_total_minutes_from_time(value),
    )


PORT_DESCRIPTIONS: list[ACInfinityPortTimeEntityDescription] = [
    ACInfinityPortTimeEntityDescription(
        key=PortControlKey.SCHEDULED_START_TIME,
        icon=None,  # default
        translation_key="schedule_mode_on_time",
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_time,
        set_value_fn=__set_value_fn_time,
    ),
    ACInfinityPortTimeEntityDescription(
        key=PortControlKey.SCHEDULED_END_TIME,
        icon=None,  # default
        translation_key="schedule_mode_off_time",
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_time,
        set_value_fn=__set_value_fn_time,
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
        super().__init__(
            coordinator, port, description.suitable_fn, description.key, Platform.TIME
        )
        self.entity_description = description

    @property
    def native_value(self) -> time | None:
        return self.entity_description.get_value_fn(self, self.port)

    async def async_set_value(self, value: time) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "%s"', self.unique_id, value
        )
        await self.entity_description.set_value_fn(self, self.port, value)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback
) -> None:
    """Set up the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    controllers = coordinator.ac_infinity.get_all_controller_properties()

    entities = ACInfinityEntities()
    for controller in controllers:
        if controller.device_type == ControllerType.UIS_89_AI_PLUS:
            # controls and settings not yet supported for the AI controller
            continue

        for port in controller.ports:
            for description in PORT_DESCRIPTIONS:
                entities.append_if_suitable(
                    ACInfinityPortTimeEntity(coordinator, description, port)
                )

    add_entities_callback(entities)
