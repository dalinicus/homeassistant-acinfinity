import logging
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityPortEntity,
    ACInfinityPortReadOnlyMixin,
)
from custom_components.ac_infinity.const import DOMAIN, SENSOR_PORT_KEY_ONLINE

from .ac_infinity import ACInfinityPort

_LOGGER = logging.getLogger(__name__)


@dataclass
class ACInfinityPortBinarySensorEntityDescription(
    BinarySensorEntityDescription, ACInfinityPortReadOnlyMixin
):
    """Describes ACInfinity Binary Sensor Entities."""


PORT_DESCRIPTIONS: list[ACInfinityPortBinarySensorEntityDescription] = [
    ACInfinityPortBinarySensorEntityDescription(
        key=SENSOR_PORT_KEY_ONLINE,
        device_class=BinarySensorDeviceClass.PLUG,
        icon="mdi:power",
        translation_key="port_online",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_property(
                port.parent_device_id, port.port_id, SENSOR_PORT_KEY_ONLINE
            )
        ),
    )
]


class ACInfinityPortBinarySensorEntity(ACInfinityPortEntity, BinarySensorEntity):
    entity_description: ACInfinityPortBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityPortBinarySensorEntityDescription,
        port: ACInfinityPort,
    ) -> None:
        super().__init__(coordinator, port, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.get_value_fn(self.ac_infinity, self.port)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    controllers = coordinator.ac_infinity.get_all_device_meta_data()

    entities: list[ACInfinityPortBinarySensorEntity] = []
    for controller in controllers:
        for port in controller.ports:
            for description in PORT_DESCRIPTIONS:
                entity = ACInfinityPortBinarySensorEntity(
                    coordinator, description, port
                )
                entities.append(entity)
                _LOGGER.info(
                    'Initializing entity "%s" for platform "%s".',
                    entity.unique_id,
                    Platform.BINARY_SENSOR,
                )

    add_entities_callback(entities)
