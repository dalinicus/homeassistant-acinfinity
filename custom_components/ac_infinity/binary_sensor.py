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

from custom_components.ac_infinity.const import DOMAIN, PortPropertyKey

from .core import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityPort,
    ACInfinityPortEntity,
    ACInfinityPortReadOnlyMixin,
    get_value_fn_port_property_default,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ACInfinityBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes ACInfinity Binary Sensor Entities."""

    key: str
    device_class: str | None
    icon: str | None
    translation_key: str | None


@dataclass
class ACInfinityPortBinarySensorEntityDescription(
    ACInfinityBinarySensorEntityDescription, ACInfinityPortReadOnlyMixin
):
    """Describes ACInfinity Binary Sensor Port Entities."""


PORT_DESCRIPTIONS: list[ACInfinityPortBinarySensorEntityDescription] = [
    ACInfinityPortBinarySensorEntityDescription(
        key=PortPropertyKey.ONLINE,
        device_class=BinarySensorDeviceClass.PLUG,
        icon="mdi:power",
        translation_key="port_online",
        get_value_fn=get_value_fn_port_property_default,
    )
]


class ACInfinityPortBinarySensorEntity(ACInfinityPortEntity, BinarySensorEntity):
    """Represents a binary sensor associated with an AC Infinity controller port"""

    entity_description: ACInfinityPortBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityPortBinarySensorEntityDescription,
        port: ACInfinityPort,
    ) -> None:
        """
        Args:
            coordinator: data coordinator responsible for updating the value of the entity.
            description: haas description used to initialize the entity.
            port: port object the entity is bound to
        """
        super().__init__(coordinator, port, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """returns true if on, false or none if off"""
        return self.entity_description.get_value_fn(self, self.port)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback
) -> None:
    """Set Up the AC Infinity BinarySensor Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
    controllers = coordinator.ac_infinity.get_all_controller_properties()

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
