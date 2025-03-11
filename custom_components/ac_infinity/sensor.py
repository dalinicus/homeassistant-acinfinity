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
    CONCENTRATION_PARTS_PER_MILLION,
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
    ACInfinitySensor,
    ACInfinitySensorEntity,
    ACInfinitySensorReadOnlyMixin,
)

from .const import (
    DOMAIN,
    ISSUE_URL,
    ControllerPropertyKey,
    ControllerType,
    CustomPortPropertyKey,
    PortPropertyKey,
    SensorPropertyKey,
    SensorReferenceKey,
    SensorType,
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
    """Describes ACInfinity Controller Sensor Entities."""


@dataclass
class ACInfinitySensorSensorEntityDescription(
    ACInfinitySensorEntityDescription, ACInfinitySensorReadOnlyMixin
):
    """Describes ACInfinity Sensor Sensor Entities"""


@dataclass
class ACInfinityPortSensorEntityDescription(
    ACInfinitySensorEntityDescription, ACInfinityPortReadOnlyMixin
):
    """Describes ACInfinity Device Sensor Entities."""


def __suitable_fn_controller_property_default(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return entity.ac_infinity.get_controller_property_exists(
        controller.device_id, entity.entity_description.key
    )


def __suitable_fn_sensor_default(entity: ACInfinityEntity, sensor: ACInfinitySensor):
    return entity.ac_infinity.get_sensor_property_exists(
        sensor.controller.device_id,
        sensor.sensor_port,
        sensor.sensor_type,
        SensorPropertyKey.SENSOR_PRECISION,
    ) and entity.ac_infinity.get_sensor_property_exists(
        sensor.controller.device_id,
        sensor.sensor_port,
        sensor.sensor_type,
        SensorPropertyKey.SENSOR_DATA,
    )


def __get_value_fn_sensor_value_default(
    entity: ACInfinityEntity, sensor: ACInfinitySensor
):
    precision = entity.ac_infinity.get_sensor_property(
        sensor.controller.device_id,
        sensor.sensor_port,
        sensor.sensor_type,
        SensorPropertyKey.SENSOR_PRECISION,
        1,
    )

    data = entity.ac_infinity.get_sensor_property(
        sensor.controller.device_id,
        sensor.sensor_port,
        sensor.sensor_type,
        SensorPropertyKey.SENSOR_DATA,
        0,
    )

    # if statement prevents floating point numbers for integer data in the UI
    return data / (10 ** (precision - 1)) if precision > 1 else data


def __suitable_fn_sensor_temperature(
    entity: ACInfinityEntity, sensor: ACInfinitySensor
):
    return (
        entity.ac_infinity.get_sensor_property_exists(
            sensor.controller.device_id,
            sensor.sensor_port,
            sensor.sensor_type,
            SensorPropertyKey.SENSOR_PRECISION,
        )
        and entity.ac_infinity.get_sensor_property_exists(
            sensor.controller.device_id,
            sensor.sensor_port,
            sensor.sensor_type,
            SensorPropertyKey.SENSOR_DATA,
        )
        and entity.ac_infinity.get_sensor_property_exists(
            sensor.controller.device_id,
            sensor.sensor_port,
            sensor.sensor_type,
            SensorPropertyKey.SENSOR_UNIT,
        )
    )


def __get_value_fn_sensor_value_temperature(
    entity: ACInfinityEntity, sensor: ACInfinitySensor
):
    precision = entity.ac_infinity.get_sensor_property(
        sensor.controller.device_id,
        sensor.sensor_port,
        sensor.sensor_type,
        SensorPropertyKey.SENSOR_PRECISION,
        1,
    )

    data = entity.ac_infinity.get_sensor_property(
        sensor.controller.device_id,
        sensor.sensor_port,
        sensor.sensor_type,
        SensorPropertyKey.SENSOR_DATA,
        0,
    )

    unit = entity.ac_infinity.get_sensor_property(
        sensor.controller.device_id,
        sensor.sensor_port,
        sensor.sensor_type,
        SensorPropertyKey.SENSOR_UNIT,
        0,
    )

    value = data / (10 ** (precision - 1)) if precision > 1 else data
    return value if unit > 0 else round((5 * (value - 32) / 9), precision - 1)


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
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="temperature",
        suitable_fn=__suitable_fn_controller_property_default,
        get_value_fn=__get_value_fn_floating_point_as_int,
    ),
    ACInfinityControllerSensorEntityDescription(
        key=ControllerPropertyKey.HUMIDITY,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="humidity",
        suitable_fn=__suitable_fn_controller_property_default,
        get_value_fn=__get_value_fn_floating_point_as_int,
    ),
    ACInfinityControllerSensorEntityDescription(
        key=ControllerPropertyKey.VPD,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.KPA,
        suggested_unit_of_measurement=None,
        icon="mdi:water-thermometer",
        translation_key="vapor_pressure_deficit",
        suitable_fn=__suitable_fn_controller_property_default,
        get_value_fn=__get_value_fn_floating_point_as_int,
    ),
]

SENSOR_DESCRIPTIONS: dict[int, ACInfinitySensorSensorEntityDescription] = {
    SensorType.PROBE_TEMPERATURE_F: ACInfinitySensorSensorEntityDescription(
        key=SensorReferenceKey.PROBE_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="probe_temperature",
        suitable_fn=__suitable_fn_sensor_temperature,
        get_value_fn=__get_value_fn_sensor_value_temperature,
    ),
    SensorType.PROBE_TEMPERATURE_C: ACInfinitySensorSensorEntityDescription(
        key=SensorReferenceKey.PROBE_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="probe_temperature",
        suitable_fn=__suitable_fn_sensor_temperature,
        get_value_fn=__get_value_fn_sensor_value_temperature,
    ),
    SensorType.PROBE_HUMIDITY: ACInfinitySensorSensorEntityDescription(
        key=SensorReferenceKey.PROBE_HUMIDITY,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="probe_humidity",
        suitable_fn=__suitable_fn_sensor_default,
        get_value_fn=__get_value_fn_sensor_value_default,
    ),
    SensorType.PROBE_VPD: ACInfinitySensorSensorEntityDescription(
        key=SensorReferenceKey.PROBE_VPD,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.KPA,
        suggested_unit_of_measurement=None,
        icon="mdi:water-thermometer",
        translation_key="probe_vapor_pressure_deficit",
        suitable_fn=__suitable_fn_sensor_default,
        get_value_fn=__get_value_fn_sensor_value_default,
    ),
    SensorType.CONTROLLER_TEMPERATURE_F: ACInfinitySensorSensorEntityDescription(
        key=SensorReferenceKey.CONTROLLER_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="controller_temperature",
        suitable_fn=__suitable_fn_sensor_temperature,
        get_value_fn=__get_value_fn_sensor_value_temperature,
    ),
    SensorType.CONTROLLER_TEMPERATURE_C: ACInfinitySensorSensorEntityDescription(
        key=SensorReferenceKey.CONTROLLER_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="controller_temperature",
        suitable_fn=__suitable_fn_sensor_temperature,
        get_value_fn=__get_value_fn_sensor_value_temperature,
    ),
    SensorType.CONTROLLER_HUMIDITY: ACInfinitySensorSensorEntityDescription(
        key=SensorReferenceKey.CONTROLLER_HUMIDITY,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="controller_humidity",
        suitable_fn=__suitable_fn_sensor_default,
        get_value_fn=__get_value_fn_sensor_value_default,
    ),
    SensorType.CONTROLLER_VPD: ACInfinitySensorSensorEntityDescription(
        key=SensorReferenceKey.CONTROLLER_VPD,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.KPA,
        suggested_unit_of_measurement=None,
        icon="mdi:water-thermometer",
        translation_key="controller_vapor_pressure_deficit",
        suitable_fn=__suitable_fn_sensor_default,
        get_value_fn=__get_value_fn_sensor_value_default,
    ),
    SensorType.CO2: ACInfinitySensorSensorEntityDescription(
        key=SensorReferenceKey.CO2_SENSOR,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="co2_sensor",
        suitable_fn=__suitable_fn_sensor_default,
        get_value_fn=__get_value_fn_sensor_value_default,
    ),
    SensorType.LIGHT: ACInfinitySensorSensorEntityDescription(
        key=SensorReferenceKey.LIGHT_SENSOR,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_unit_of_measurement=None,
        icon="mdi:lightbulb-on-outline",
        translation_key="light_sensor",
        suitable_fn=__suitable_fn_sensor_default,
        get_value_fn=__get_value_fn_sensor_value_default,
    ),
}

PORT_DESCRIPTIONS: list[ACInfinityPortSensorEntityDescription] = [
    ACInfinityPortSensorEntityDescription(
        key=PortPropertyKey.SPEAK,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,  # no units / bare integer value
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="current_power",
        suitable_fn=__suitable_fn_port_property_default,
        get_value_fn=__get_value_fn_port_property_default,
    ),
    ACInfinityPortSensorEntityDescription(
        key=PortPropertyKey.REMAINING_TIME,
        device_class=SensorDeviceClass.DURATION,
        state_class=None,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="remaining_time",
        suitable_fn=__suitable_fn_port_property_default,
        get_value_fn=__get_value_fn_port_property_default,
    ),
    ACInfinityPortSensorEntityDescription(
        key=CustomPortPropertyKey.NEXT_STATE_CHANGE,
        device_class=SensorDeviceClass.TIMESTAMP,
        state_class=None,
        native_unit_of_measurement=None,
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="next_state_change",
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


class ACInfinitySensorSensorEntity(ACInfinitySensorEntity, SensorEntity):
    entity_description: ACInfinitySensorSensorEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinitySensorSensorEntityDescription,
        sensor: ACInfinitySensor,
    ) -> None:
        super().__init__(coordinator, sensor, description.suitable_fn, Platform.SENSOR)
        self.entity_description = description

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self.entity_description.get_value_fn(self, self.sensor)


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
            if controller.device_type == ControllerType.UIS_89_AI_PLUS:
                # The AI controller has two temperature measurements; controller temperature and probe temperature.
                # These values are available in the sensor array.  The external values are duplicated on the old fields used by
                # the non-AI controllers. We use the sensor array values as the source of truth, and choose not to duplicate them here.
                continue

            entity = ACInfinityControllerSensorEntity(
                coordinator, description, controller
            )
            entities.append_if_suitable(entity)

        for sensor in controller.sensors:
            if sensor.sensor_type in SENSOR_DESCRIPTIONS:
                description = SENSOR_DESCRIPTIONS[sensor.sensor_type]
                entity = ACInfinitySensorSensorEntity(coordinator, description, sensor)
                entities.append_if_suitable(entity)
            else:
                logging.warning(
                    'Unknown sensor type "%s". Please fill out an issue at %s with this error message.',
                    sensor.sensor_type,
                    ISSUE_URL,
                )

        for port in controller.ports:
            for description in PORT_DESCRIPTIONS:
                entity = ACInfinityPortSensorEntity(coordinator, description, port)
                entities.append_if_suitable(entity)

    add_entities_callback(entities)
