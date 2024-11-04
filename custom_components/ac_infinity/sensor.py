import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    Platform,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import StateType
from zoneinfo import ZoneInfo

from custom_components.ac_infinity.core import (
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

from .const import (
    DOMAIN,
    ControllerPropertyKey,
    CustomPortPropertyKey,
    PortPropertyKey,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ACInfinitySensorEntityDescription(SensorEntityDescription):
    """Describes ACInfinity Number Sensor Entities."""

    key: str
    icon: str | None
    translation_key: str | None
    device_class: SensorDeviceClass | None
    native_unit_of_measurement: str | None
    state_class: SensorStateClass | str | None
    suggested_unit_of_measurement: str | None


@dataclass
class ACInfinityControllerSensorEntityDescription(
    ACInfinitySensorEntityDescription, ACInfinityControllerReadOnlyMixin
):
    """Describes ACInfinity Number Sensor Entities."""


@dataclass
class ACInfinityPortSensorEntityDescription(
    ACInfinitySensorEntityDescription, ACInfinityPortReadOnlyMixin
):
    """Describes ACInfinity Number Sensor Entities."""


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


def __get_value_fn_port_property_default(
    entity: ACInfinityEntity, port: ACInfinityPort
):
    return entity.ac_infinity.get_port_property(
        port.controller.device_id, port.port_index, entity.entity_description.key, 0
    )


def __get_value_fn_floating_point_as_int(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    # value stored as an integer, but represents a 2 digit precision float
    return (
        entity.ac_infinity.get_controller_property(
            controller.device_id, entity.entity_description.key, 0
        )
        / 100
    )


def __get_next_mode_change_timestamp(
    entity: ACInfinityEntity, port: ACInfinityPort
) -> datetime | None:
    remaining_seconds = entity.ac_infinity.get_port_property(
        port.controller.device_id, port.port_index, PortPropertyKey.REMAINING_TIME, 0
    )

    timezone = entity.ac_infinity.get_controller_property(
        port.controller.device_id, ControllerPropertyKey.TIME_ZONE
    )

    if remaining_seconds <= 0:
        return None

    return datetime.now(ZoneInfo(timezone)) + timedelta(seconds=remaining_seconds)


CONTROLLER_DESCRIPTIONS: list[ACInfinityControllerSensorEntityDescription] = [
    ACInfinityControllerSensorEntityDescription(
        key=ControllerPropertyKey.TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon=None,  # default
        translation_key="temperature",
        suggested_unit_of_measurement=None,
        suitable_fn=__suitable_fn_controller_property_default,
        get_value_fn=__get_value_fn_floating_point_as_int,
    ),
    ACInfinityControllerSensorEntityDescription(
        key=ControllerPropertyKey.HUMIDITY,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon=None,  # default
        translation_key="humidity",
        suggested_unit_of_measurement=None,
        suitable_fn=__suitable_fn_controller_property_default,
        get_value_fn=__get_value_fn_floating_point_as_int,
    ),
    ACInfinityControllerSensorEntityDescription(
        key=ControllerPropertyKey.VPD,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_unit_of_measurement=UnitOfPressure.KPA,
        native_unit_of_measurement=UnitOfPressure.KPA,
        icon="mdi:water-thermometer",
        translation_key="vapor_pressure_deficit",
        suitable_fn=__suitable_fn_controller_property_default,
        get_value_fn=__get_value_fn_floating_point_as_int,
    ),
]

PORT_DESCRIPTIONS: list[ACInfinityPortSensorEntityDescription] = [
    ACInfinityPortSensorEntityDescription(
        key=PortPropertyKey.SPEAK,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,  # no units / bare integer value
        icon=None,  # default
        translation_key="current_power",
        suggested_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_property_default,
        get_value_fn=__get_value_fn_port_property_default,
    ),
    ACInfinityPortSensorEntityDescription(
        key=PortPropertyKey.REMAINING_TIME,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        icon=None,  # default
        translation_key="remaining_time",
        suggested_unit_of_measurement=None,
        state_class=None,
        suitable_fn=__suitable_fn_port_property_default,
        get_value_fn=__get_value_fn_port_property_default,
    ),
    ACInfinityPortSensorEntityDescription(
        key=CustomPortPropertyKey.NEXT_STATE_CHANGE,
        device_class=SensorDeviceClass.TIMESTAMP,
        native_unit_of_measurement=None,
        icon=None,  # default
        translation_key="next_state_change",
        suggested_unit_of_measurement=None,
        state_class=None,
        suitable_fn=lambda x, y: True,
        get_value_fn=__get_next_mode_change_timestamp,
    ),
]


class ACInfinityControllerSensorEntity(ACInfinityControllerEntity, SensorEntity):
    entity_description: ACInfinityControllerSensorEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityControllerSensorEntityDescription,
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
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self.entity_description.get_value_fn(self, self.controller)


class ACInfinityPortSensorEntity(ACInfinityPortEntity, SensorEntity):
    entity_description: ACInfinityPortSensorEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityPortSensorEntityDescription,
        port: ACInfinityPort,
    ) -> None:
        super().__init__(
            coordinator, port, description.suitable_fn, description.key, Platform.SENSOR
        )
        self.entity_description = description

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self.entity_description.get_value_fn(self, self.port)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback
) -> None:
    """Set up the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    controllers = coordinator.ac_infinity.get_all_controller_properties()

    entities = ACInfinityEntities()
    for controller in controllers:
        for description in CONTROLLER_DESCRIPTIONS:
            entity = ACInfinityControllerSensorEntity(
                coordinator, description, controller
            )
            entities.append_if_suitable(entity)

        for port in controller.ports:
            for description in PORT_DESCRIPTIONS:
                entity = ACInfinityPortSensorEntity(coordinator, description, port)
                entities.append_if_suitable(entity)

    add_entities_callback(entities)
