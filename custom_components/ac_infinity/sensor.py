import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from custom_components.ac_infinity import (
    ACInfinityControllerEntity,
    ACInfinityControllerReadOnlyMixin,
    ACInfinityDataUpdateCoordinator,
    ACInfinityPortEntity,
    ACInfinityPortReadOnlyMixin,
)
from custom_components.ac_infinity.ac_infinity import (
    ACInfinityController,
    ACInfinityPort,
)

from .const import (
    DOMAIN,
    SENSOR_KEY_HUMIDITY,
    SENSOR_KEY_TEMPERATURE,
    SENSOR_KEY_VPD,
    SENSOR_PORT_KEY_SPEAK,
    SENSOR_SETTING_KEY_SURPLUS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ACInfinityControllerSensorEntityDescription(
    SensorEntityDescription, ACInfinityControllerReadOnlyMixin
):
    """Describes ACInfinity Number Sensor Entities."""


@dataclass
class ACInfinityPortSensorEntityDescription(
    SensorEntityDescription, ACInfinityPortReadOnlyMixin
):
    """Describes ACInfinity Number Sensor Entities."""


CONTROLLER_DESCRIPTIONS: list[ACInfinityControllerSensorEntityDescription] = [
    ACInfinityControllerSensorEntityDescription(
        key=SENSOR_KEY_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon=None,  # default
        translation_key="temperature",
        get_value_fn=lambda ac_infinity, controller: (
            # value stored as an integer, but represents a 2 digit precision float
            ac_infinity.get_device_property(
                controller.device_id, SENSOR_KEY_TEMPERATURE
            )
            / 100
        ),
    ),
    ACInfinityControllerSensorEntityDescription(
        key=SENSOR_KEY_HUMIDITY,
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        icon=None,  # default
        translation_key="humidity",
        get_value_fn=lambda ac_infinity, controller: (
            # value stored as an integer, but represents a 2 digit precision float
            ac_infinity.get_device_property(controller.device_id, SENSOR_KEY_HUMIDITY)
            / 100
        ),
    ),
    ACInfinityControllerSensorEntityDescription(
        key=SENSOR_KEY_VPD,
        device_class=SensorDeviceClass.PRESSURE,
        suggested_unit_of_measurement=UnitOfPressure.KPA,
        native_unit_of_measurement=UnitOfPressure.KPA,
        icon="mdi:water-thermometer",
        translation_key="vapor_pressure_deficit",
        get_value_fn=lambda ac_infinity, controller: (
            # value stored as an integer, but represents a 2 digit precision float
            ac_infinity.get_device_property(controller.device_id, SENSOR_KEY_VPD)
            / 100
        ),
    ),
]

PORT_DESCRIPTIONS: list[ACInfinityPortSensorEntityDescription] = [
    ACInfinityPortSensorEntityDescription(
        key=SENSOR_PORT_KEY_SPEAK,
        device_class=SensorDeviceClass.POWER_FACTOR,
        native_unit_of_measurement=None,  # no units / bare integer value
        icon=None,  # default
        translation_key="current_power",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_property(
                port.parent_device_id, port.port_id, SENSOR_PORT_KEY_SPEAK
            )
        ),
    ),
    ACInfinityPortSensorEntityDescription(
        key=SENSOR_SETTING_KEY_SURPLUS,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        icon=None,  # default
        translation_key="remaining_time",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SENSOR_SETTING_KEY_SURPLUS
            )
            or 0
        ),
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
        super().__init__(coordinator, controller, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self.entity_description.get_value_fn(self.ac_infinity, self.controller)


class ACInfinityPortSensorEntity(ACInfinityPortEntity, SensorEntity):
    entity_description: ACInfinityPortSensorEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityPortSensorEntityDescription,
        port: ACInfinityPort,
    ) -> None:
        super().__init__(coordinator, port, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self.entity_description.get_value_fn(self.ac_infinity, self.port)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    controllers = coordinator.ac_infinity.get_all_device_meta_data()

    entities = []
    for controller in controllers:
        for description in CONTROLLER_DESCRIPTIONS:
            entity = ACInfinityControllerSensorEntity(
                coordinator, description, controller
            )
            entities.append(entity)
            _LOGGER.info(
                'Initializing entity "%s" for platform "%s".',
                entity.unique_id,
                Platform.SENSOR,
            )

        for port in controller.ports:
            for description in PORT_DESCRIPTIONS:
                entity = ACInfinityPortSensorEntity(coordinator, description, port)
                entities.append(entity)
                _LOGGER.info(
                    'Initializing entity "%s" for platform "%s".',
                    entity.unique_id,
                    Platform.SENSOR,
                )

    add_entities_callback(entities)
