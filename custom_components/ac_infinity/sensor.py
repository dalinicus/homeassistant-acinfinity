import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

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

from custom_components.ac_infinity.core import (
    ACInfinityController,
    ACInfinityControllerEntity,
    ACInfinityControllerReadOnlyMixin,
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntities,
    ACInfinityEntity,
    ACInfinityDevice,
    ACInfinityDeviceEntity,
    ACInfinityDeviceReadOnlyMixin,
    ACInfinitySensor,
    ACInfinitySensorEntity,
    ACInfinitySensorReadOnlyMixin, enabled_fn_sensor,
)

from .const import (
    DOMAIN,
    ISSUE_URL,
    ControllerPropertyKey,
    CustomDevicePropertyKey,
    DevicePropertyKey,
    SensorPropertyKey,
    SensorReferenceKey,
    SensorType, ControllerType,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ACInfinitySensorEntityDescription(SensorEntityDescription):
    """Describes ACInfinity Number Sensor Entities."""

    key: str
    icon: str | None
    translation_key: str | None
    device_class: SensorDeviceClass | None
    native_unit_of_measurement: str | None
    state_class: SensorStateClass | str | None
    suggested_unit_of_measurement: str | None


@dataclass(frozen=True)
class ACInfinityControllerSensorEntityDescription(
    ACInfinitySensorEntityDescription, ACInfinityControllerReadOnlyMixin
):
    """Describes ACInfinity Controller Sensor Entities."""


@dataclass(frozen=True)
class ACInfinitySensorSensorEntityDescription(
    ACInfinitySensorEntityDescription, ACInfinitySensorReadOnlyMixin
):
    """Describes ACInfinity Sensor Sensor Entities"""


@dataclass(frozen=True)
class ACInfinityDeviceSensorEntityDescription(
    ACInfinitySensorEntityDescription, ACInfinityDeviceReadOnlyMixin
):
    """Describes ACInfinity Device Sensor Entities."""


def __suitable_fn_controller_property_default(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    # The AI controller have two temperature measurements; controller temperature and probe temperature.
    # These values are available in the sensor array.  The external values are duplicated on the base fields used by
    # the non-AI controllers. We use the sensor array values as the source of truth, and choose not to duplicate them here
    # by skipping the controller descriptions for the base values.
    return not controller.is_ai_controller and entity.ac_infinity.get_controller_property_exists(
        controller.controller_id, entity.data_key
    )


def __suitable_fn_sensor_default(entity: ACInfinityEntity, sensor: ACInfinitySensor):
    return entity.ac_infinity.get_sensor_property_exists(
        sensor.controller.controller_id,
        sensor.sensor_port,
        sensor.sensor_type,
        SensorPropertyKey.SENSOR_PRECISION,
    ) and entity.ac_infinity.get_sensor_property_exists(
        sensor.controller.controller_id,
        sensor.sensor_port,
        sensor.sensor_type,
        SensorPropertyKey.SENSOR_DATA,
    )


def __get_value_fn_sensor_value_default(
    entity: ACInfinityEntity, sensor: ACInfinitySensor
):
    precision = entity.ac_infinity.get_sensor_property(
        sensor.controller.controller_id,
        sensor.sensor_port,
        sensor.sensor_type,
        SensorPropertyKey.SENSOR_PRECISION,
        1,
    )

    data = entity.ac_infinity.get_sensor_property(
        sensor.controller.controller_id,
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
            sensor.controller.controller_id,
            sensor.sensor_port,
            sensor.sensor_type,
            SensorPropertyKey.SENSOR_PRECISION,
        )
        and entity.ac_infinity.get_sensor_property_exists(
            sensor.controller.controller_id,
            sensor.sensor_port,
            sensor.sensor_type,
            SensorPropertyKey.SENSOR_DATA,
        )
        and entity.ac_infinity.get_sensor_property_exists(
            sensor.controller.controller_id,
            sensor.sensor_port,
            sensor.sensor_type,
            SensorPropertyKey.SENSOR_UNIT,
        )
    )


def __get_value_fn_sensor_value_temperature(
    entity: ACInfinityEntity, sensor: ACInfinitySensor
):
    precision = entity.ac_infinity.get_sensor_property(
        sensor.controller.controller_id,
        sensor.sensor_port,
        sensor.sensor_type,
        SensorPropertyKey.SENSOR_PRECISION,
        1,
    )

    data = entity.ac_infinity.get_sensor_property(
        sensor.controller.controller_id,
        sensor.sensor_port,
        sensor.sensor_type,
        SensorPropertyKey.SENSOR_DATA,
        0,
    )

    unit = entity.ac_infinity.get_sensor_property(
        sensor.controller.controller_id,
        sensor.sensor_port,
        sensor.sensor_type,
        SensorPropertyKey.SENSOR_UNIT,
        0,
    )

    value = data / (10 ** (precision - 1)) if precision > 1 else data
    return value if unit > 0 else round((5 * (value - 32) / 9), precision - 1)


def __suitable_fn_device_property_default(entity: ACInfinityEntity, device: ACInfinityDevice):
    return entity.ac_infinity.get_device_property_exists(
        device.controller.controller_id, device.device_port, entity.data_key
    )


def __get_value_fn_device_property_default(
    entity: ACInfinityEntity, device: ACInfinityDevice
):
    return entity.ac_infinity.get_device_property(
        device.controller.controller_id, device.device_port, entity.data_key, 0
    )


def __get_value_fn_floating_point_as_int(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    # value stored as an integer, but represents a 2 digit precision float
    return (
        entity.ac_infinity.get_controller_property(
            controller.controller_id, entity.data_key, 0
        )
        / 100
    )


def __get_next_mode_change_timestamp(
    entity: ACInfinityEntity, device: ACInfinityDevice
) -> datetime | None:
    remaining_seconds = entity.ac_infinity.get_device_property(
        device.controller.controller_id, device.device_port, DevicePropertyKey.REMAINING_TIME, 0
    )

    timezone = entity.ac_infinity.get_controller_property(
        device.controller.controller_id, ControllerPropertyKey.TIME_ZONE
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
        enabled_fn=enabled_fn_sensor,
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
        enabled_fn=enabled_fn_sensor,
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
        enabled_fn=enabled_fn_sensor,
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
        enabled_fn=enabled_fn_sensor,
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
        enabled_fn=enabled_fn_sensor,
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
        enabled_fn=enabled_fn_sensor,
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
        enabled_fn=enabled_fn_sensor,
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
        enabled_fn=enabled_fn_sensor,
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
        enabled_fn=enabled_fn_sensor,
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
        enabled_fn=enabled_fn_sensor,
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
        enabled_fn=enabled_fn_sensor,
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
        enabled_fn=enabled_fn_sensor,
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
        enabled_fn=enabled_fn_sensor,
        suitable_fn=__suitable_fn_sensor_default,
        get_value_fn=__get_value_fn_sensor_value_default,
    ),
    SensorType.SOIL: ACInfinitySensorSensorEntityDescription(
        key=SensorReferenceKey.SOIL,
        device_class=SensorDeviceClass.MOISTURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_unit_of_measurement=None,
        icon="mdi:watering-can-outline",
        translation_key="soil_sensor",
        enabled_fn=enabled_fn_sensor,
        suitable_fn=__suitable_fn_sensor_default,
        get_value_fn=__get_value_fn_sensor_value_default,
    ),
}

DEVICE_DESCRIPTIONS: list[ACInfinityDeviceSensorEntityDescription] = [
    ACInfinityDeviceSensorEntityDescription(
        key=DevicePropertyKey.SPEAK,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,  # no units / bare integer value
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="current_power",
        enabled_fn=enabled_fn_sensor,
        suitable_fn=__suitable_fn_device_property_default,
        get_value_fn=__get_value_fn_device_property_default,
    ),
    ACInfinityDeviceSensorEntityDescription(
        key=DevicePropertyKey.REMAINING_TIME,
        device_class=SensorDeviceClass.DURATION,
        state_class=None,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="remaining_time",
        enabled_fn=enabled_fn_sensor,
        suitable_fn=__suitable_fn_device_property_default,
        get_value_fn=__get_value_fn_device_property_default,
    ),
    ACInfinityDeviceSensorEntityDescription(
        key=CustomDevicePropertyKey.NEXT_STATE_CHANGE,
        device_class=SensorDeviceClass.TIMESTAMP,
        state_class=None,
        native_unit_of_measurement=None,
        suggested_unit_of_measurement=None,
        icon=None,  # default
        translation_key="next_state_change",
        enabled_fn=enabled_fn_sensor,
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
            description.enabled_fn,
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
        super().__init__(
            coordinator,
            sensor,
            description.enabled_fn,
            description.suitable_fn,
            description.key,
            Platform.SENSOR,
        )
        self.entity_description = description

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self.entity_description.get_value_fn(self, self.sensor)


class ACInfinityDeviceSensorEntity(ACInfinityDeviceEntity, SensorEntity):
    entity_description: ACInfinityDeviceSensorEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityDeviceSensorEntityDescription,
        device: ACInfinityDevice,
    ) -> None:
        super().__init__(
            coordinator, device, description.enabled_fn, description.suitable_fn, description.key, Platform.SENSOR
        )
        self.entity_description = description

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self.entity_description.get_value_fn(self, self.device_port)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback
) -> None:
    """Set up the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    controllers = coordinator.ac_infinity.get_all_controller_properties()

    entities = ACInfinityEntities(config)
    for controller in controllers:
        for controller_description in CONTROLLER_DESCRIPTIONS:
            controller_entity = ACInfinityControllerSensorEntity(
                coordinator, controller_description, controller
            )
            entities.append_if_suitable(controller_entity)

        for sensor in controller.sensors:
            if sensor.sensor_type in SENSOR_DESCRIPTIONS:
                sensor_description = SENSOR_DESCRIPTIONS[sensor.sensor_type]
                sensor_entity = ACInfinitySensorSensorEntity(
                    coordinator, sensor_description, sensor
                )
                entities.append_if_suitable(sensor_entity)
            elif sensor.sensor_type not in SensorType.__dict__.values():
                logging.warning(
                    'Unknown sensor type "%s". Please fill out an issue at %s with this error message.',
                    sensor.sensor_type,
                    ISSUE_URL,
                )

        for device in controller.devices:
            for device_description in DEVICE_DESCRIPTIONS:
                device_entity = ACInfinityDeviceSensorEntity(
                    coordinator, device_description, device
                )
                entities.append_if_suitable(device_entity)

    add_entities_callback(entities)
