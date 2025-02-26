import logging
import math
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant

from custom_components.ac_infinity.const import (
    DOMAIN,
    AdvancedSettingsKey,
    ControllerType,
    PortControlKey,
)
from custom_components.ac_infinity.core import (
    ACInfinityController,
    ACInfinityControllerEntity,
    ACInfinityControllerReadWriteMixin,
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntities,
    ACInfinityEntity,
    ACInfinityPort,
    ACInfinityPortEntity,
    ACInfinityPortReadWriteMixin,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ACInfinityNumberEntityDescription(NumberEntityDescription):
    """Describes ACInfinity Number Entities"""

    key: str
    icon: str | None
    translation_key: str | None
    device_class: NumberDeviceClass | None
    mode: NumberMode | None
    native_max_value: float | None
    native_min_value: float | None
    native_step: float | None
    native_unit_of_measurement: str | None


@dataclass
class ACInfinityControllerNumberEntityDescription(
    ACInfinityNumberEntityDescription, ACInfinityControllerReadWriteMixin
):
    """Describes ACInfinity Number Controller Entities."""


@dataclass
class ACInfinityPortNumberEntityDescription(
    ACInfinityNumberEntityDescription, ACInfinityPortReadWriteMixin
):
    """Describes ACInfinity Number Port Entities."""


def __suitable_fn_controller_setting_default(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return entity.ac_infinity.get_controller_setting_exists(
        controller.device_id, entity.entity_description.key
    )


def __suitable_fn_port_control_default(entity: ACInfinityEntity, port: ACInfinityPort):
    return entity.ac_infinity.get_port_control_exists(
        port.controller.device_id, port.port_index, entity.entity_description.key
    )


def __suitable_fn_port_setting_default(entity: ACInfinityEntity, port: ACInfinityPort):
    return entity.ac_infinity.get_port_setting_exists(
        port.controller.device_id, port.port_index, entity.entity_description.key
    )


def __get_value_fn_controller_setting_default(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return entity.ac_infinity.get_controller_setting(
        controller.device_id, entity.entity_description.key, 0
    )


def __get_value_fn_port_control_default(entity: ACInfinityEntity, port: ACInfinityPort):
    return entity.ac_infinity.get_port_control(
        port.controller.device_id, port.port_index, entity.entity_description.key, 0
    )


def __get_value_fn_port_setting_default(entity: ACInfinityEntity, port: ACInfinityPort):
    return entity.ac_infinity.get_port_setting(
        port.controller.device_id, port.port_index, entity.entity_description.key, 0
    )


def __get_value_fn_cal_temp(entity: ACInfinityEntity, controller: ACInfinityController):
    temp_unit = entity.ac_infinity.get_controller_setting(
        controller.device_id, AdvancedSettingsKey.TEMP_UNIT, 0
    )
    return entity.ac_infinity.get_controller_setting(
        controller.device_id,
        AdvancedSettingsKey.CALIBRATE_TEMP
        if temp_unit > 0
        else AdvancedSettingsKey.CALIBRATE_TEMP_F,
        0,
    )


def __get_value_fn_vpd_leaf_temp_offset(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        controller.device_id, AdvancedSettingsKey.TEMP_UNIT, 0
    )
    return entity.ac_infinity.get_controller_setting(
        controller.device_id,
        AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET
        if temp_unit > 0
        else AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET_F,
        0,
    )


def __get_value_fn_timer_duration(entity: ACInfinityEntity, port: ACInfinityPort):
    # value configured as minutes but stored as seconds
    return (
        entity.ac_infinity.get_port_control(
            port.controller.device_id, port.port_index, entity.entity_description.key, 0
        )
        / 60
    )


def __get_value_fn_vpd_control(entity: ACInfinityEntity, port: ACInfinityPort):
    # value configured as percent (10.2%) but stored as tenths of a percent (102)
    return (
        entity.ac_infinity.get_port_control(
            port.controller.device_id, port.port_index, entity.entity_description.key, 0
        )
        / 10
    )


def __get_value_fn_vpd_setting(entity: ACInfinityEntity, port: ACInfinityPort):
    # value configured as percent (10.2%) but stored as tenths of a percent (102)
    return (
        entity.ac_infinity.get_port_setting(
            port.controller.device_id, port.port_index, entity.entity_description.key, 0
        )
        / 10
    )


def __get_value_fn_dynamic_transition_temp(
    entity: ACInfinityEntity, port: ACInfinityPort
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        port.controller.device_id, AdvancedSettingsKey.TEMP_UNIT, 0
    )

    return entity.ac_infinity.get_port_setting(
        port.controller.device_id,
        port.port_index,
        AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP
        if temp_unit > 0
        else AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP_F,
        0,
    )


def __get_value_fn_dynamic_buffer_temp(entity: ACInfinityEntity, port: ACInfinityPort):
    temp_unit = entity.ac_infinity.get_controller_setting(
        port.controller.device_id, AdvancedSettingsKey.TEMP_UNIT, 0
    )

    return entity.ac_infinity.get_port_setting(
        port.controller.device_id,
        port.port_index,
        AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP
        if temp_unit > 0
        else AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP_F,
        0,
    )


def __set_value_fn_port_setting_default(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    return entity.ac_infinity.update_port_setting(
        port.controller.device_id, port.port_index, entity.entity_description.key, value
    )


def __set_value_fn_port_control_default(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    return entity.ac_infinity.update_port_control(
        port.controller.device_id, port.port_index, entity.entity_description.key, value
    )


def __set_value_fn_controller_setting_default(
    entity: ACInfinityEntity, controller: ACInfinityController, value: int
):
    return entity.ac_infinity.update_controller_setting(
        controller.device_id, entity.entity_description.key, value
    )


def __set_value_fn_cal_temp(
    entity: ACInfinityEntity, controller: ACInfinityController, value: int
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        controller.device_id, AdvancedSettingsKey.TEMP_UNIT
    )

    # in the event that the user swaps from F to C in the ac infinity app without reloading homeassistant,
    # we need to put bounds on the value since the entity min/max values will still be ±20 instead of ±10
    if temp_unit > 0 and value > 10:
        value = 10
    elif temp_unit > 0 and value < -10:
        value = -10

    return entity.ac_infinity.update_controller_settings(
        controller.device_id,
        [
            (AdvancedSettingsKey.CALIBRATE_TEMP, value),
            (AdvancedSettingsKey.CALIBRATE_TEMP_F, 0),
        ]
        if temp_unit > 0
        else [
            (AdvancedSettingsKey.CALIBRATE_TEMP, 0),
            (AdvancedSettingsKey.CALIBRATE_TEMP_F, value),
        ],
    )


def __set_value_fn_vpd_leaf_temp_offset(
    entity: ACInfinityEntity, controller: ACInfinityController, value: int
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        controller.device_id, AdvancedSettingsKey.TEMP_UNIT
    )

    # in the event that the user swaps from F to C in the ac infinity app without reloading homeassistant,
    # we need to put bounds on the value since the entity min/max values will still be ±20 instead of ±10
    if temp_unit > 0 and value > 10:
        value = 10
    elif temp_unit > 0 and value < -10:
        value = -10

    return entity.ac_infinity.update_controller_setting(
        controller.device_id,
        AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET
        if temp_unit > 0
        else AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET_F,
        value,
    )


def __set_value_fn_timer_duration(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    # value configured as minutes but stored as seconds
    return entity.ac_infinity.update_port_control(
        port.controller.device_id,
        port.port_index,
        entity.entity_description.key,
        value * 60,
    )


def __set_value_fn_vpd_control(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    # value configured as percent (10.2%) but stored as tenths of a percent (102)
    return entity.ac_infinity.update_port_control(
        port.controller.device_id,
        port.port_index,
        entity.entity_description.key,
        value * 10,
    )


def __set_value_fn_vpd_setting(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    # value configured as percent (10.2%) but stored as tenths of a percent (102)
    return entity.ac_infinity.update_port_setting(
        port.controller.device_id,
        port.port_index,
        entity.entity_description.key,
        value * 10,
    )


def __set_value_fn_temp_auto_low(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    return entity.ac_infinity.update_port_controls(
        port.controller.device_id,
        port.port_index,
        [
            # value is received from HA as C
            (PortControlKey.AUTO_TEMP_LOW_TRIGGER, value),
            # degrees F must be calculated and set in addition to C
            (PortControlKey.AUTO_TEMP_LOW_TRIGGER_F, int(round((value * 1.8) + 32, 0))),
        ],
    )


def __set_value_fn_temp_auto_high(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    return entity.ac_infinity.update_port_controls(
        port.controller.device_id,
        port.port_index,
        [
            # value is received from HA as C
            (PortControlKey.AUTO_TEMP_HIGH_TRIGGER, value),
            # degrees F must be calculated and set in addition to C
            (
                PortControlKey.AUTO_TEMP_HIGH_TRIGGER_F,
                int(round((value * 1.8) + 32, 0)),
            ),
        ],
    )


def __set_value_fn_target_temp(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    return entity.ac_infinity.update_port_controls(
        port.controller.device_id,
        port.port_index,
        [
            # value is received from HA as C
            (PortControlKey.AUTO_TARGET_TEMP, value),
            # degrees F must be calculated and set in addition to C
            (PortControlKey.AUTO_TARGET_TEMP_F, int(round((value * 1.8) + 32, 0))),
        ],
    )


def __set_value_fn_dynamic_transition_temp(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        port.controller.device_id, AdvancedSettingsKey.TEMP_UNIT
    )

    # in the event that the user swaps from F to C in the ac infinity app without reloading homeassistant,
    # we need to put bounds on the value since the entity max values will still be 20 instead of 10
    if temp_unit > 0 and value > 10:
        value = 10

    return entity.ac_infinity.update_port_settings(
        port.controller.device_id,
        port.port_index,
        [
            (AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP, value),
            (AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP_F, value * 2),
        ]
        if temp_unit > 0
        else [
            (AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP, math.floor(value / 2)),
            (AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP_F, value),
        ],
    )


def __set_value_fn_dynamic_buffer_temp(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        port.controller.device_id, AdvancedSettingsKey.TEMP_UNIT
    )

    # in the event that the user swaps from F to C in the ac infinity app without reloading homeassistant,
    # we need to put bounds on the value since the entity max values will still be 20 instead of 10
    if temp_unit > 0 and value > 10:
        value = 10

    return entity.ac_infinity.update_port_settings(
        port.controller.device_id,
        port.port_index,
        [
            (AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP, value),
            (AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP_F, value * 2),
        ]
        if temp_unit > 0
        else [
            (AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP, math.floor(value / 2)),
            (AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP_F, value),
        ],
    )


CONTROLLER_DESCRIPTIONS: list[ACInfinityControllerNumberEntityDescription] = [
    ACInfinityControllerNumberEntityDescription(
        key=AdvancedSettingsKey.CALIBRATE_TEMP,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=-20,
        native_max_value=20,
        native_step=1,
        icon="mdi:thermometer-plus",
        translation_key="temperature_calibration",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_controller_setting_default,
        get_value_fn=__get_value_fn_cal_temp,
        set_value_fn=__set_value_fn_cal_temp,
    ),
    ACInfinityControllerNumberEntityDescription(
        key=AdvancedSettingsKey.CALIBRATE_HUMIDITY,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=-10,
        native_max_value=10,
        native_step=1,
        icon="mdi:cloud-percent-outline",
        translation_key="humidity_calibration",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_controller_setting_default,
        get_value_fn=__get_value_fn_controller_setting_default,
        set_value_fn=__set_value_fn_controller_setting_default,
    ),
    ACInfinityControllerNumberEntityDescription(
        key=AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=-20,
        native_max_value=20,
        native_step=1,
        icon="mdi:leaf",
        translation_key="vpd_leaf_temperature_offset",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_controller_setting_default,
        get_value_fn=__get_value_fn_vpd_leaf_temp_offset,
        set_value_fn=__set_value_fn_vpd_leaf_temp_offset,
    ),
]

PORT_DESCRIPTIONS: list[ACInfinityPortNumberEntityDescription] = [
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.ON_SPEED,
        device_class=NumberDeviceClass.POWER_FACTOR,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:knob",
        translation_key="on_power",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_port_control_default,
        set_value_fn=__set_value_fn_port_control_default,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.OFF_SPEED,
        device_class=NumberDeviceClass.POWER_FACTOR,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:knob",
        translation_key="off_power",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_port_control_default,
        set_value_fn=__set_value_fn_port_control_default,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.TIMER_DURATION_TO_ON,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="timer_mode_minutes_to_on",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_timer_duration,
        set_value_fn=__set_value_fn_timer_duration,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.TIMER_DURATION_TO_OFF,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="timer_mode_minutes_to_off",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_timer_duration,
        set_value_fn=__set_value_fn_timer_duration,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.CYCLE_DURATION_ON,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="cycle_mode_minutes_on",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_timer_duration,
        set_value_fn=__set_value_fn_timer_duration,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.CYCLE_DURATION_OFF,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="cycle_mode_minutes_off",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_timer_duration,
        set_value_fn=__set_value_fn_timer_duration,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.VPD_LOW_TRIGGER,
        device_class=NumberDeviceClass.PRESSURE,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=9.9,
        native_step=0.1,
        icon="mdi:water-thermometer-outline",
        translation_key="vpd_mode_low_trigger",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_vpd_control,
        set_value_fn=__set_value_fn_vpd_control,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.VPD_HIGH_TRIGGER,
        device_class=NumberDeviceClass.PRESSURE,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=9.9,
        native_step=0.1,
        icon="mdi:water-thermometer-outline",
        translation_key="vpd_mode_high_trigger",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_vpd_control,
        set_value_fn=__set_value_fn_vpd_control,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.VPD_TARGET,
        device_class=NumberDeviceClass.PRESSURE,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=9.9,
        native_step=0.1,
        icon="mdi:water-thermometer-outline",
        translation_key="target_vpd",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_vpd_control,
        set_value_fn=__set_value_fn_vpd_control,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.AUTO_HUMIDITY_LOW_TRIGGER,
        device_class=NumberDeviceClass.HUMIDITY,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        icon="mdi:water-percent",
        translation_key="auto_mode_humidity_low_trigger",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_port_control_default,
        set_value_fn=__set_value_fn_port_control_default,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.AUTO_HUMIDITY_HIGH_TRIGGER,
        device_class=NumberDeviceClass.HUMIDITY,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        icon="mdi:water-percent",
        translation_key="auto_mode_humidity_high_trigger",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_port_control_default,
        set_value_fn=__set_value_fn_port_control_default,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.AUTO_TARGET_HUMIDITY,
        device_class=NumberDeviceClass.HUMIDITY,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        icon="mdi:water-percent",
        translation_key="target_humidity",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_port_control_default,
        set_value_fn=__set_value_fn_port_control_default,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.AUTO_TEMP_LOW_TRIGGER,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=90,
        native_step=1,
        icon=None,
        translation_key="auto_mode_temp_low_trigger",
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_port_control_default,
        set_value_fn=__set_value_fn_temp_auto_low,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.AUTO_TEMP_HIGH_TRIGGER,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=90,
        native_step=1,
        icon=None,
        translation_key="auto_mode_temp_high_trigger",
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_port_control_default,
        set_value_fn=__set_value_fn_temp_auto_high,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortControlKey.AUTO_TARGET_TEMP,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=90,
        native_step=1,
        icon=None,
        translation_key="target_temp",
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_port_control_default,
        set_value_fn=__set_value_fn_target_temp,
    ),
    ACInfinityPortNumberEntityDescription(
        key=AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=20,
        native_step=1,
        icon="mdi:thermometer-plus",
        translation_key="dynamic_transition_temp",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_setting_default,
        get_value_fn=__get_value_fn_dynamic_transition_temp,
        set_value_fn=__set_value_fn_dynamic_transition_temp,
    ),
    ACInfinityPortNumberEntityDescription(
        key=AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:cloud-percent-outline",
        translation_key="dynamic_transition_humidity",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_setting_default,
        get_value_fn=__get_value_fn_port_setting_default,
        set_value_fn=__set_value_fn_port_setting_default,
    ),
    ACInfinityPortNumberEntityDescription(
        key=AdvancedSettingsKey.DYNAMIC_TRANSITION_VPD,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=1,
        native_step=0.1,
        icon="mdi:leaf",
        translation_key="dynamic_transition_vpd",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_setting_default,
        get_value_fn=__get_value_fn_vpd_setting,
        set_value_fn=__set_value_fn_vpd_setting,
    ),
    ACInfinityPortNumberEntityDescription(
        key=AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=20,
        native_step=1,
        icon="mdi:thermometer-plus",
        translation_key="dynamic_buffer_temp",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_setting_default,
        get_value_fn=__get_value_fn_dynamic_buffer_temp,
        set_value_fn=__set_value_fn_dynamic_buffer_temp,
    ),
    ACInfinityPortNumberEntityDescription(
        key=AdvancedSettingsKey.DYNAMIC_BUFFER_HUMIDITY,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:cloud-percent-outline",
        translation_key="dynamic_buffer_humidity",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_setting_default,
        get_value_fn=__get_value_fn_port_setting_default,
        set_value_fn=__set_value_fn_port_setting_default,
    ),
    ACInfinityPortNumberEntityDescription(
        key=AdvancedSettingsKey.DYNAMIC_BUFFER_VPD,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=1,
        native_step=0.1,
        icon="mdi:leaf",
        translation_key="dynamic_buffer_vpd",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_setting_default,
        get_value_fn=__get_value_fn_vpd_setting,
        set_value_fn=__set_value_fn_vpd_setting,
    ),
    ACInfinityPortNumberEntityDescription(
        key=AdvancedSettingsKey.SUNRISE_TIMER_DURATION,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=360,
        native_step=1,
        icon=None,  # default
        translation_key="sunrise_timer_minutes",
        native_unit_of_measurement=None,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_port_setting_default,
        set_value_fn=__set_value_fn_port_setting_default,
    ),
]


class ACInfinityControllerNumberEntity(ACInfinityControllerEntity, NumberEntity):
    entity_description: ACInfinityControllerNumberEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityControllerNumberEntityDescription,
        controller: ACInfinityController,
    ) -> None:
        super().__init__(
            coordinator,
            controller,
            description.suitable_fn,
            description.key,
            Platform.NUMBER,
        )
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.entity_description.get_value_fn(self, self.controller)

    async def async_set_native_value(self, value: float) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "%s"', self.unique_id, value
        )
        await self.entity_description.set_value_fn(self, self.controller, value)
        await self.coordinator.async_request_refresh()


class ACInfinityPortNumberEntity(ACInfinityPortEntity, NumberEntity):
    entity_description: ACInfinityPortNumberEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityPortNumberEntityDescription,
        port: ACInfinityPort,
    ) -> None:
        super().__init__(
            coordinator, port, description.suitable_fn, description.key, Platform.NUMBER
        )
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.entity_description.get_value_fn(self, self.port)

    async def async_set_native_value(self, value: float) -> None:
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

        temp_unit = coordinator.ac_infinity.get_controller_setting(
            controller.device_id, AdvancedSettingsKey.TEMP_UNIT
        )
        for description in CONTROLLER_DESCRIPTIONS:
            entity = ACInfinityControllerNumberEntity(
                coordinator, description, controller
            )

            if temp_unit > 0 and description.key in (
                AdvancedSettingsKey.CALIBRATE_TEMP,
                AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET,
            ):
                # Celsius is restricted to ±10C versus Fahrenheit which is restricted to ±20F
                entity.entity_description.native_min_value = -10
                entity.entity_description.native_max_value = 10

            entities.append_if_suitable(entity)

        for port in controller.ports:
            for description in PORT_DESCRIPTIONS:
                entity = ACInfinityPortNumberEntity(coordinator, description, port)
                if temp_unit > 0 and description.key in (
                    AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP,
                    AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP,
                ):
                    # Celsius max value is 10C versus Fahrenheit which maxes out at 20F
                    entity.entity_description.native_max_value = 10

                entities.append_if_suitable(entity)

    add_entities_callback(entities)
