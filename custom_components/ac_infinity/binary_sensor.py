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

from custom_components.ac_infinity.const import (
    DOMAIN,
    ControllerPropertyKey,
    PortPropertyKey,
)

from .core import (
    ACInfinityController,
    ACInfinityControllerEntity,
    ACInfinityControllerReadOnlyMixin,
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntities,
    ACInfinityEntity,
    ACInfinityPort,
    ACInfinityPortEntity,
    ACInfinityPortReadOnlyMixin,
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
class ACInfinityControllerBinarySensorEntityDescription(
    ACInfinityBinarySensorEntityDescription, ACInfinityControllerReadOnlyMixin
):
    """Describes ACInfinity Binary Sensor Port Entities."""


@dataclass
class ACInfinityPortBinarySensorEntityDescription(
    ACInfinityBinarySensorEntityDescription, ACInfinityPortReadOnlyMixin
):
    """Describes ACInfinity Binary Sensor Port Entities."""


def __suitable_fn_controller_property_default(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return entity.ac_infinity.get_controller_property_exists(
        controller.device_id, entity.entity_description.key
    )


def __suitable_fn_port_property_default(entity: ACInfinityEntity, port: ACInfinityPort):
    return entity.ac_infinity.get_port_property_exists(
        port.controller.device_id, port.port_index, entity.entity_description.key
    )


def __get_value_fn_controller_property_default(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return entity.ac_infinity.get_controller_property(
        controller.device_id, entity.entity_description.key, False
    )


def __get_value_fn_port_property_default(
    entity: ACInfinityEntity, port: ACInfinityPort
):
    return entity.ac_infinity.get_port_property(
        port.controller.device_id, port.port_index, entity.entity_description.key, False
    )


CONTROLLER_DESCRIPTIONS: list[ACInfinityControllerBinarySensorEntityDescription] = [
    ACInfinityControllerBinarySensorEntityDescription(
        key=ControllerPropertyKey.ONLINE,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:power-plug",
        translation_key="controller_online",
        suitable_fn=__suitable_fn_controller_property_default,
        get_value_fn=__get_value_fn_controller_property_default,
    )
]

PORT_DESCRIPTIONS: list[ACInfinityPortBinarySensorEntityDescription] = [
    ACInfinityPortBinarySensorEntityDescription(
        key=PortPropertyKey.ONLINE,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:power-plug",
        translation_key="port_online",
        suitable_fn=__suitable_fn_port_property_default,
        get_value_fn=__get_value_fn_port_property_default,
    ),
    ACInfinityPortBinarySensorEntityDescription(
        key=PortPropertyKey.STATE,
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:power",
        translation_key="port_state",
        suitable_fn=__suitable_fn_port_property_default,
        get_value_fn=__get_value_fn_port_property_default,
    ),
]


class ACInfinityControllerBinarySensorEntity(
    ACInfinityControllerEntity, BinarySensorEntity
):
    entity_description: ACInfinityControllerBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityControllerBinarySensorEntityDescription,
        controller: ACInfinityController,
    ) -> None:
        super().__init__(
            coordinator,
            controller,
            description.suitable_fn,
            description.key,
            Platform.SENSOR,
        )
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """returns true if on, false or none if off"""
        return self.entity_description.get_value_fn(self, self.controller)


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
        super().__init__(
            coordinator,
            port,
            description.suitable_fn,
            description.key,
            Platform.BINARY_SENSOR,
        )
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

    entities = ACInfinityEntities()
    for controller in controllers:
        for description in CONTROLLER_DESCRIPTIONS:
            entity = ACInfinityControllerBinarySensorEntity(
                coordinator, description, controller
            )
            entities.append_if_suitable(entity)

        for port in controller.ports:
            for description in PORT_DESCRIPTIONS:
                entity = ACInfinityPortBinarySensorEntity(
                    coordinator, description, port
                )
                entities.append_if_suitable(entity)

    add_entities_callback(entities)
