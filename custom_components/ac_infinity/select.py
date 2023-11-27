import logging
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
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
from custom_components.ac_infinity.const import DOMAIN, SETTING_KEY_AT_TYPE

_LOGGER = logging.getLogger(__name__)


@dataclass
class ACInfinityPortSelectEntityDescription(
    SelectEntityDescription, ACInfinityPortReadWriteMixin
):
    """Describes ACInfinity Select Entities."""


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

PORT_DESCRIPTIONS: list[ACInfinityPortSelectEntityDescription] = [
    ACInfinityPortSelectEntityDescription(
        key=SETTING_KEY_AT_TYPE,
        translation_key="active_mode",
        options=MODE_OPTIONS,
        get_value_fn=lambda ac_infinity, port: (
            MODE_OPTIONS[
                # data is 1 based.  Adjust to 0 based enum by subtracting 1
                ac_infinity.get_device_port_setting(
                    port.parent_device_id, port.port_id, SETTING_KEY_AT_TYPE
                )
                - 1
            ]
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_AT_TYPE,
                # data is 1 based.  Adjust from 0 based enum by adding 1
                MODE_OPTIONS.index(value) + 1,
            )
        ),
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
        return self.entity_description.get_value_fn(self.ac_infinity, self.port)

    async def async_select_option(self, option: str) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "%s"',
            self.unique_id,
            option,
        )
        await self.entity_description.set_value_fn(self.ac_infinity, self.port, option)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    coordintator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    controllers = coordintator.ac_infinity.get_all_device_meta_data()

    entities = []
    for controller in controllers:
        for port in controller.ports:
            for description in PORT_DESCRIPTIONS:
                entity = ACInfinityPortSelectEntity(coordintator, description, port)
                entities.append(entity)
                _LOGGER.info(
                    'Initializing entity "%s" for platform "%s".',
                    entity.unique_id,
                    Platform.SELECT,
                )

    add_entities_callback(entities)
