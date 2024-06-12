import logging
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from custom_components.ac_infinity.const import DOMAIN, PortSettingKey
from custom_components.ac_infinity.core import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntity,
    ACInfinityPort,
    ACInfinityPortEntity,
    ACInfinityPortReadWriteMixin,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ACInfinitySelectEntityDescription(SelectEntityDescription):
    """Describes ACInfinity Select Entities."""

    key: str
    translation_key: str | None
    options: list[str] | None


@dataclass
class ACInfinityPortSelectEntityDescription(
    ACInfinitySelectEntityDescription, ACInfinityPortReadWriteMixin
):
    """Describes ACInfinity Select Port Entities."""


MODE_OPTIONS = [
    "Off",
    "On",
    "Auto",
    "Timer to On",
    "Timer to Off",
    "Cycle",
    "Schedule",
    "VPD",
]


def __get_value_fn_active_mode(entity: ACInfinityEntity, port: ACInfinityPort):
    return MODE_OPTIONS[
        # data is 1 based.  Adjust to 0 based enum by subtracting 1
        entity.ac_infinity.get_port_setting(
            port.controller.device_id, port.port_index, PortSettingKey.AT_TYPE
        )
        - 1
    ]


def __set_value_fn_active_mode(
    entity: ACInfinityEntity, port: ACInfinityPort, value: str
):
    return entity.ac_infinity.update_port_setting(
        port.controller.device_id,
        port.port_index,
        PortSettingKey.AT_TYPE,
        # data is 1 based.  Adjust from 0 based enum by adding 1
        MODE_OPTIONS.index(value) + 1,
    )


PORT_DESCRIPTIONS: list[ACInfinityPortSelectEntityDescription] = [
    ACInfinityPortSelectEntityDescription(
        key=PortSettingKey.AT_TYPE,
        translation_key="active_mode",
        options=MODE_OPTIONS,
        get_value_fn=__get_value_fn_active_mode,
        set_value_fn=__set_value_fn_active_mode,
    )
]


class ACInfinityPortSelectEntity(ACInfinityPortEntity, SelectEntity):
    entity_description: ACInfinityPortSelectEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityPortSelectEntityDescription,
        port: ACInfinityPort,
    ) -> None:
        super().__init__(coordinator, port, description.key)
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        return self.entity_description.get_value_fn(self, self.port)

    async def async_select_option(self, option: str) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "%s"',
            self.unique_id,
            option,
        )
        await self.entity_description.set_value_fn(self, self.port, option)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback
) -> None:
    """Set up the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    controllers = coordinator.ac_infinity.get_all_controller_properties()

    entities = []
    for controller in controllers:
        for port in controller.ports:
            for description in PORT_DESCRIPTIONS:
                entity = ACInfinityPortSelectEntity(coordinator, description, port)
                entities.append(entity)
                _LOGGER.info(
                    'Initializing entity "%s" for platform "%s".',
                    entity.unique_id,
                    Platform.SELECT,
                )

    add_entities_callback(entities)
