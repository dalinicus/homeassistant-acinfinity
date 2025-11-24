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
    AtType, DOMAIN, AdvancedSettingsKey, DeviceControlKey,
)
from custom_components.ac_infinity.core import (
    ACInfinityController,
    ACInfinityControllerEntity,
    ACInfinityControllerReadWriteMixin,
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntities,
    ACInfinityEntity,
    ACInfinityDevice,
    ACInfinityDeviceEntity,
    ACInfinityDeviceReadWriteMixin, enabled_fn_setting, enabled_fn_control,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class ACInfinityControllerNumberEntityDescription(
    ACInfinityNumberEntityDescription, ACInfinityControllerReadWriteMixin[float]
):
    """Describes ACInfinity Number Controller Entities."""


@dataclass(frozen=True)
class ACInfinityDeviceNumberEntityDescription(
    ACInfinityNumberEntityDescription, ACInfinityDeviceReadWriteMixin[float]
):
    """Describes ACInfinity Number Port Entities."""


def __suitable_fn_controller_setting_temp_impl(
    entity: ACInfinityEntity, controller: ACInfinityController, desired_temp_unit: int
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        controller.controller_id, AdvancedSettingsKey.TEMP_UNIT, 0
    )

    if temp_unit == desired_temp_unit:
        return entity.ac_infinity.get_controller_setting_exists(
            controller.controller_id, entity.data_key
        )
    return False


def __suitable_fn_controller_setting_temp_f(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return not controller.is_ai_controller and __suitable_fn_controller_setting_temp_impl(entity, controller, 0)


def __suitable_fn_controller_setting_temp_c(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return not controller.is_ai_controller and __suitable_fn_controller_setting_temp_impl(entity, controller, 1)


def __suitable_fn_controller_setting_default(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return not controller.is_ai_controller and entity.ac_infinity.get_controller_setting_exists(
        controller.controller_id, entity.data_key
    )


def __suitable_fn_device_control_default(entity: ACInfinityEntity, device: ACInfinityDevice):
    return entity.ac_infinity.get_device_control_exists(
        device.controller.controller_id, device.device_port, entity.data_key
    )

def __suitable_fn_device_control_basic_controller(entity: ACInfinityEntity, device: ACInfinityDevice):
    return not device.controller.is_ai_controller and entity.ac_infinity.get_device_control_exists(
        device.controller.controller_id, device.device_port, entity.data_key
    )

def __suitable_fn_device_control_ai_controller(entity: ACInfinityEntity, device: ACInfinityDevice):
    return device.controller.is_ai_controller and entity.ac_infinity.get_device_control_exists(
        device.controller.controller_id, device.device_port, entity.data_key
    )

def __suitable_fn_device_setting_default(entity: ACInfinityEntity, device: ACInfinityDevice):
    return not device.controller.is_ai_controller and entity.ac_infinity.get_device_setting_exists(
        device.controller.controller_id, device.device_port, entity.data_key
    )


def __suitable_fn_device_setting_temp_impl(
    entity: ACInfinityEntity, device: ACInfinityDevice, desired_temp_unit: int
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        device.controller.controller_id, AdvancedSettingsKey.TEMP_UNIT, 0
    )

    if temp_unit == desired_temp_unit:
        return entity.ac_infinity.get_device_setting_exists(
            device.controller.controller_id, device.device_port, entity.data_key
        )
    return False


def __suitable_fn_device_setting_temp_f(entity: ACInfinityEntity, device: ACInfinityDevice):
    return not device.controller.is_ai_controller and __suitable_fn_device_setting_temp_impl(entity, device, 0)


def __suitable_fn_device_setting_temp_c(entity: ACInfinityEntity, device: ACInfinityDevice):
    return not device.controller.is_ai_controller and __suitable_fn_device_setting_temp_impl(entity, device, 1)


def __get_value_fn_controller_setting_default(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return entity.ac_infinity.get_controller_setting(
        controller.controller_id, entity.data_key, 0
    )


def __get_value_fn_device_control_default(entity: ACInfinityEntity, device: ACInfinityDevice):
    return entity.ac_infinity.get_device_control(
        device.controller.controller_id, device.device_port, entity.data_key, 0
    )


def __get_value_fn_device_setting_default(entity: ACInfinityEntity, device: ACInfinityDevice):
    return entity.ac_infinity.get_device_setting(
        device.controller.controller_id, device.device_port, entity.data_key, 0
    )


def __get_value_fn_cal_temp(entity: ACInfinityEntity, controller: ACInfinityController):
    temp_unit = entity.ac_infinity.get_controller_setting(
        controller.controller_id, AdvancedSettingsKey.TEMP_UNIT, 0
    )
    return entity.ac_infinity.get_controller_setting(
        controller.controller_id,
        (
            AdvancedSettingsKey.CALIBRATE_TEMP
            if temp_unit > 0
            else AdvancedSettingsKey.CALIBRATE_TEMP_F
        ),
        0,
    )


def __get_value_fn_vpd_leaf_temp_offset(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        controller.controller_id, AdvancedSettingsKey.TEMP_UNIT, 0
    )
    return entity.ac_infinity.get_controller_setting(
        controller.controller_id,
        (
            AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET
            if temp_unit > 0
            else AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET_F
        ),
        0,
    )


def __get_value_fn_timer_duration(entity: ACInfinityEntity, device: ACInfinityDevice):
    # value configured as minutes but stored as seconds
    return (
        entity.ac_infinity.get_device_control(
            device.controller.controller_id, device.device_port, entity.data_key, 0
        )
        / 60
    )


def __get_value_fn_vpd_control(entity: ACInfinityEntity, device: ACInfinityDevice):
    # value configured as percent (10.2%) but stored as tenths of a percent (102)
    return (
        entity.ac_infinity.get_device_control(
            device.controller.controller_id, device.device_port, entity.data_key, 0
        )
        / 10
    )


def __get_value_fn_vpd_setting(entity: ACInfinityEntity, device: ACInfinityDevice):
    # value configured as percent (10.2%) but stored as tenths of a percent (102)
    return (
        entity.ac_infinity.get_device_setting(
            device.controller.controller_id, device.device_port, entity.data_key, 0
        )
        / 10
    )


def __get_value_fn_dynamic_transition_temp(
    entity: ACInfinityEntity, device: ACInfinityDevice
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        device.controller.controller_id, AdvancedSettingsKey.TEMP_UNIT, 0
    )

    return entity.ac_infinity.get_device_setting(
        device.controller.controller_id,
        device.device_port,
        (
            AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP
            if temp_unit > 0
            else AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP_F
        ),
        0,
    )


def __get_value_fn_dynamic_buffer_temp(entity: ACInfinityEntity, device: ACInfinityDevice):
    temp_unit = entity.ac_infinity.get_controller_setting(
        device.controller.controller_id, AdvancedSettingsKey.TEMP_UNIT, 0
    )

    return entity.ac_infinity.get_device_setting(
        device.controller.controller_id,
        device.device_port,
        (
            AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP
            if temp_unit > 0
            else AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP_F
        ),
        0,
    )


def __set_value_fn_device_setting_default(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: float
):
    return entity.ac_infinity.update_device_setting(device, entity.data_key, int(value or 0))


def __set_value_fn_device_control_default(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: float
):
    return entity.ac_infinity.update_device_control(device, entity.data_key, int(value or 0))


def __set_value_fn_controller_setting_default(
    entity: ACInfinityEntity, controller: ACInfinityController, value: float
):
    return entity.ac_infinity.update_controller_setting(
        controller, entity.data_key, int(value or 0)
    )


def __set_value_fn_cal_temp(
    entity: ACInfinityEntity, controller: ACInfinityController, value: float
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        controller.controller_id, AdvancedSettingsKey.TEMP_UNIT
    )

    # in the event that the user swaps from F to C in the ac infinity app without reloading homeassistant,
    # we need to put bounds on the value since the entity min/max values will still be ±20 instead of ±10
    if temp_unit > 0 and value > 10:
        value = 10
    elif temp_unit > 0 and value < -10:
        value = -10

    return entity.ac_infinity.update_controller_settings(
        controller,
        (
            {
                AdvancedSettingsKey.CALIBRATE_TEMP: int(value or 0),
                AdvancedSettingsKey.CALIBRATE_TEMP_F: 0,
            }
            if temp_unit > 0
            else {
                AdvancedSettingsKey.CALIBRATE_TEMP: 0,
                AdvancedSettingsKey.CALIBRATE_TEMP_F: int(value or 0),
            }
        ),
    )


def __set_value_fn_vpd_leaf_temp_offset(
    entity: ACInfinityEntity, controller: ACInfinityController, value: float
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        controller.controller_id, AdvancedSettingsKey.TEMP_UNIT
    )

    # in the event that the user swaps from F to C in the ac infinity app without reloading homeassistant,
    # we need to put bounds on the value since the entity min/max values will still be ±20 instead of ±10
    if temp_unit > 0 and value > 10:
        value = 10
    elif temp_unit > 0 and value < -10:
        value = -10

    return entity.ac_infinity.update_controller_setting(
        controller,
        (
            AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET
            if temp_unit > 0
            else AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET_F
        ),
        int(value or 0),
    )


def __set_value_fn_timer_duration(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: float
):
    # value configured as minutes but stored as seconds
    return entity.ac_infinity.update_device_control(device, entity.data_key, int((value or 0) * 60))


def __set_value_fn_vpd_control(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: float
):
    # value configured as percent (10.2%) but stored as tenths of a percent (102)
    return entity.ac_infinity.update_device_control(device, entity.data_key, int((value or 0) * 10))


def __set_value_fn_vpd_setting(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: float
):
    # value configured as percent (10.2%) but stored as tenths of a percent (102)
    return entity.ac_infinity.update_device_setting(device, entity.data_key, int((value or 0) * 10))


def __set_value_fn_temp_auto_low(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: float
):
    return entity.ac_infinity.update_device_controls(
        device,
        {
            # value is received from HA as C
            DeviceControlKey.AUTO_TEMP_LOW_TRIGGER: int(value or 0),
            # degrees F must be calculated and set in addition to C
            DeviceControlKey.AUTO_TEMP_LOW_TRIGGER_F: int(round((value * 1.8) + 32, 0)),
        },
    )


def __set_value_fn_temp_auto_high(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: float
):
    return entity.ac_infinity.update_device_controls(
        device,
        {
            # value is received from HA as C
            DeviceControlKey.AUTO_TEMP_HIGH_TRIGGER: int(value or 0),
            # degrees F must be calculated and set in addition to C
            DeviceControlKey.AUTO_TEMP_HIGH_TRIGGER_F: int(round((value * 1.8) + 32, 0)),
        },
    )


def __set_value_fn_target_temp(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: float
):
    return entity.ac_infinity.update_device_controls(
        device,
        {
            # value is received from HA as C
            DeviceControlKey.TARGET_TEMP: int(value or 0),
            # degrees F must be calculated and set in addition to C
            DeviceControlKey.TARGET_TEMP_F: int(round((value * 1.8) + 32, 0)),
        },
    )


def __set_value_fn_dynamic_transition_temp(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: float
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        device.controller.controller_id, AdvancedSettingsKey.TEMP_UNIT
    )

    # in the event that the user swaps from F to C in the ac infinity app without reloading homeassistant,
    # we need to put bounds on the value since the entity max values will still be 20 instead of 10
    if temp_unit > 0 and value > 10:
        value = 10

    return entity.ac_infinity.update_device_settings(
        device,
        (
            {
                AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP: int(value or 0),
                AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP_F: int(value or 0) * 2,
            }
            if temp_unit > 0
            else
            {
                AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP: math.floor(int(value or 0) / 2),
                AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP_F: int(value or 0),
            }
        ),
    )


def __set_value_fn_dynamic_buffer_temp(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: float
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        device.controller.controller_id, AdvancedSettingsKey.TEMP_UNIT
    )

    # in the event that the user swaps from F to C in the ac infinity app without reloading homeassistant,
    # we need to put bounds on the value since the entity max values will still be 20 instead of 10
    if temp_unit > 0 and value > 10:
        value = 10

    return entity.ac_infinity.update_device_settings(
        device,
        (
            {
                AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP: int(value or 0),
                AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP_F: int(value or 0) * 2,
            }
            if temp_unit > 0
            else {
                AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP: math.floor(int(value or 0) / 2),
                AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP_F: int(value or 0),
            }
        ),
    )


CONTROLLER_DESCRIPTIONS: list[ACInfinityControllerNumberEntityDescription] = [
    ACInfinityControllerNumberEntityDescription(
        # F - native value +-20
        key=AdvancedSettingsKey.CALIBRATE_TEMP,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=-20,
        native_max_value=20,
        native_step=1,
        icon="mdi:thermometer-plus",
        translation_key="temperature_calibration",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_controller_setting_temp_f,
        get_value_fn=__get_value_fn_cal_temp,
        set_value_fn=__set_value_fn_cal_temp,
    ),
    ACInfinityControllerNumberEntityDescription(
        # F - native value +-10
        key=AdvancedSettingsKey.CALIBRATE_TEMP,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=-10,
        native_max_value=10,
        native_step=1,
        icon="mdi:thermometer-plus",
        translation_key="temperature_calibration",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_controller_setting_temp_c,
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
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_controller_setting_default,
        get_value_fn=__get_value_fn_controller_setting_default,
        set_value_fn=__set_value_fn_controller_setting_default,
    ),
    ACInfinityControllerNumberEntityDescription(
        # F - native value +-20
        key=AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=-20,
        native_max_value=20,
        native_step=1,
        icon="mdi:leaf",
        translation_key="vpd_leaf_temperature_offset",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_controller_setting_temp_f,
        get_value_fn=__get_value_fn_vpd_leaf_temp_offset,
        set_value_fn=__set_value_fn_vpd_leaf_temp_offset,
    ),
    ACInfinityControllerNumberEntityDescription(
        # C - native value +-10
        key=AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=-10,
        native_max_value=10,
        native_step=1,
        icon="mdi:leaf",
        translation_key="vpd_leaf_temperature_offset",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_controller_setting_temp_c,
        get_value_fn=__get_value_fn_vpd_leaf_temp_offset,
        set_value_fn=__set_value_fn_vpd_leaf_temp_offset,
    ),
]

DEVICE_DESCRIPTIONS: list[ACInfinityDeviceNumberEntityDescription] = [
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.ON_SPEED,
        device_class=NumberDeviceClass.POWER_FACTOR,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:knob",
        translation_key="on_power",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_basic_controller,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
        at_type_fn=lambda at_type: True
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.OFF_SPEED,
        device_class=NumberDeviceClass.POWER_FACTOR,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:knob",
        translation_key="off_power",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_basic_controller,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
        at_type_fn=lambda at_type: True
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.ON_SELF_SPEED,
        device_class=NumberDeviceClass.POWER_FACTOR,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:knob",
        translation_key="on_power",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_ai_controller,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
        at_type_fn=lambda at_type: at_type != AtType.OFF
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.TIMER_DURATION_TO_ON,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="timer_mode_minutes_to_on",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_timer_duration,
        set_value_fn=__set_value_fn_timer_duration,
        at_type_fn=lambda at_type: at_type == AtType.TIMER_TO_ON
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.TIMER_DURATION_TO_OFF,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="timer_mode_minutes_to_off",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_timer_duration,
        set_value_fn=__set_value_fn_timer_duration,
        at_type_fn=lambda at_type: at_type == AtType.TIMER_TO_OFF
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.CYCLE_DURATION_ON,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="cycle_mode_minutes_on",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_timer_duration,
        set_value_fn=__set_value_fn_timer_duration,
        at_type_fn=lambda at_type: at_type == AtType.CYCLE
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.CYCLE_DURATION_OFF,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="cycle_mode_minutes_off",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_timer_duration,
        set_value_fn=__set_value_fn_timer_duration,
        at_type_fn=lambda at_type: at_type == AtType.CYCLE
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.VPD_LOW_TRIGGER,
        device_class=NumberDeviceClass.PRESSURE,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=9.9,
        native_step=0.1,
        icon="mdi:water-thermometer-outline",
        translation_key="vpd_mode_low_trigger",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_vpd_control,
        set_value_fn=__set_value_fn_vpd_control,
        at_type_fn=lambda at_type: at_type == AtType.VPD
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.VPD_HIGH_TRIGGER,
        device_class=NumberDeviceClass.PRESSURE,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=9.9,
        native_step=0.1,
        icon="mdi:water-thermometer-outline",
        translation_key="vpd_mode_high_trigger",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_vpd_control,
        set_value_fn=__set_value_fn_vpd_control,
        at_type_fn=lambda at_type: at_type == AtType.VPD
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.TARGET_VPD,
        device_class=NumberDeviceClass.PRESSURE,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=9.9,
        native_step=0.1,
        icon="mdi:water-thermometer-outline",
        translation_key="target_vpd",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_vpd_control,
        set_value_fn=__set_value_fn_vpd_control,
        at_type_fn=lambda at_type: at_type == AtType.VPD
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.AUTO_HUMIDITY_LOW_TRIGGER,
        device_class=NumberDeviceClass.HUMIDITY,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        icon="mdi:water-percent",
        translation_key="auto_mode_humidity_low_trigger",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
        at_type_fn=lambda at_type: at_type == AtType.AUTO
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.AUTO_HUMIDITY_HIGH_TRIGGER,
        device_class=NumberDeviceClass.HUMIDITY,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        icon="mdi:water-percent",
        translation_key="auto_mode_humidity_high_trigger",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
        at_type_fn=lambda at_type: at_type == AtType.AUTO
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.TARGET_HUMI,
        device_class=NumberDeviceClass.HUMIDITY,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        icon="mdi:water-percent",
        translation_key="target_humidity",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
        at_type_fn=lambda at_type: at_type == AtType.AUTO
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.AUTO_TEMP_LOW_TRIGGER,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=90,
        native_step=1,
        icon=None,
        translation_key="auto_mode_temp_low_trigger",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_temp_auto_low,
        at_type_fn=lambda at_type: at_type == AtType.AUTO
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.AUTO_TEMP_HIGH_TRIGGER,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=90,
        native_step=1,
        icon=None,
        translation_key="auto_mode_temp_high_trigger",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_temp_auto_high,
        at_type_fn=lambda at_type: at_type == AtType.AUTO
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=DeviceControlKey.TARGET_TEMP,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=90,
        native_step=1,
        icon=None,
        translation_key="target_temp",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_target_temp,
        at_type_fn=lambda at_type: at_type == AtType.AUTO
    ),
    ACInfinityDeviceNumberEntityDescription(
        # F - native value 0-20
        key=AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=20,
        native_step=1,
        icon="mdi:thermometer-plus",
        translation_key="dynamic_transition_temp",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_device_setting_temp_f,
        get_value_fn=__get_value_fn_dynamic_transition_temp,
        set_value_fn=__set_value_fn_dynamic_transition_temp,
        at_type_fn=lambda at_type: True
    ),
    ACInfinityDeviceNumberEntityDescription(
        # C - native value 0-10
        key=AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:thermometer-plus",
        translation_key="dynamic_transition_temp",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_device_setting_temp_c,
        get_value_fn=__get_value_fn_dynamic_transition_temp,
        set_value_fn=__set_value_fn_dynamic_transition_temp,
        at_type_fn=lambda at_type: True
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:cloud-percent-outline",
        translation_key="dynamic_transition_humidity",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_device_setting_default,
        get_value_fn=__get_value_fn_device_setting_default,
        set_value_fn=__set_value_fn_device_setting_default,
        at_type_fn=lambda at_type: True
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=AdvancedSettingsKey.DYNAMIC_TRANSITION_VPD,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=1,
        native_step=0.1,
        icon="mdi:leaf",
        translation_key="dynamic_transition_vpd",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_device_setting_default,
        get_value_fn=__get_value_fn_vpd_setting,
        set_value_fn=__set_value_fn_vpd_setting,
        at_type_fn=lambda at_type: True
    ),
    ACInfinityDeviceNumberEntityDescription(
        # F - native value 0-20
        key=AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=20,
        native_step=1,
        icon="mdi:thermometer-plus",
        translation_key="dynamic_buffer_temp",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_device_setting_temp_f,
        get_value_fn=__get_value_fn_dynamic_buffer_temp,
        set_value_fn=__set_value_fn_dynamic_buffer_temp,
        at_type_fn=lambda at_type: True
    ),
    ACInfinityDeviceNumberEntityDescription(
        # C - native value 0-10
        key=AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:thermometer-plus",
        translation_key="dynamic_buffer_temp",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_device_setting_temp_c,
        get_value_fn=__get_value_fn_dynamic_buffer_temp,
        set_value_fn=__set_value_fn_dynamic_buffer_temp,
        at_type_fn=lambda at_type: True
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=AdvancedSettingsKey.DYNAMIC_BUFFER_HUMIDITY,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:cloud-percent-outline",
        translation_key="dynamic_buffer_humidity",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_device_setting_default,
        get_value_fn=__get_value_fn_device_setting_default,
        set_value_fn=__set_value_fn_device_setting_default,
        at_type_fn=lambda at_type: True
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=AdvancedSettingsKey.DYNAMIC_BUFFER_VPD,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=1,
        native_step=0.1,
        icon="mdi:leaf",
        translation_key="dynamic_buffer_vpd",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_device_setting_default,
        get_value_fn=__get_value_fn_vpd_setting,
        set_value_fn=__set_value_fn_vpd_setting,
        at_type_fn=lambda at_type: True
    ),
    ACInfinityDeviceNumberEntityDescription(
        key=AdvancedSettingsKey.SUNRISE_TIMER_DURATION,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=360,
        native_step=1,
        icon=None,  # default
        translation_key="sunrise_timer_minutes",
        native_unit_of_measurement=None,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_device_setting_default,
        get_value_fn=__get_value_fn_device_setting_default,
        set_value_fn=__set_value_fn_device_setting_default,
        at_type_fn=lambda at_type: True
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
            description.enabled_fn,
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


class ACInfinityDeviceNumberEntity(ACInfinityDeviceEntity, NumberEntity):
    entity_description: ACInfinityDeviceNumberEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityDeviceNumberEntityDescription,
        device: ACInfinityDevice,
    ) -> None:
        super().__init__(
            coordinator, device, description.enabled_fn, description.suitable_fn, description.at_type_fn, description.key, Platform.NUMBER
        )
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.entity_description.get_value_fn(self, self.device_port)

    async def async_set_native_value(self, value: float) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "%s"', self.unique_id, value
        )
        await self.entity_description.set_value_fn(self, self.device_port, value)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback
) -> None:
    """Set up the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
    controllers = coordinator.ac_infinity.get_all_controller_properties()

    entities = ACInfinityEntities(config)
    for controller in controllers:

        for controller_description in CONTROLLER_DESCRIPTIONS:
            controller_entity = ACInfinityControllerNumberEntity(
                coordinator, controller_description, controller
            )

            entities.append_if_suitable(controller_entity)

        for device in controller.devices:
            for device_description in DEVICE_DESCRIPTIONS:
                device_entity = ACInfinityDeviceNumberEntity(
                    coordinator, device_description, device
                )

                entities.append_if_suitable(device_entity)

    add_entities_callback(entities)
