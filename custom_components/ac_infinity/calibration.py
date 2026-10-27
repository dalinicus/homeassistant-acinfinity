"""Calibrate a controller's built-in temperature / humidity sensor against another sensor in Home Assistant.

The offset is written to the controller's own calibration setting, so the controller's triggers and display use the
corrected value too, not just Home Assistant.  The offset is computed from the raw (uncalibrated) reading, so
calibrating repeatedly - e.g. from an automation - converges on the same value instead of stacking offsets.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import AdvancedSettingsKey, ControllerPropertyKey
from .core import ACInfinityController, ACInfinityService

# the controller's accepted calibration ranges, matching the calibration number entities
TEMP_RANGE_C = 10
TEMP_RANGE_F = 20
HUMIDITY_RANGE = 10


@dataclass
class CalibrationResult:
    temperature_offset: int | None = None
    temperature_unit: str | None = None
    humidity_offset: int | None = None
    clamped: bool = False


def read_reference(hass: HomeAssistant, entity_id: str, temperature: bool) -> float:
    """The reference sensor's current value; temperatures are converted to °C."""
    state = hass.states.get(entity_id)
    if state is None:
        raise HomeAssistantError(f"Reference sensor {entity_id} does not exist")
    try:
        value = float(state.state)
    except ValueError as ex:
        raise HomeAssistantError(f"Reference sensor {entity_id} has no numeric value ({state.state})") from ex

    if temperature:
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, UnitOfTemperature.CELSIUS)
        value = TemperatureConverter.convert(value, unit, UnitOfTemperature.CELSIUS)
    return value


def __clamp(value: float, limit: int) -> tuple[int, bool]:
    rounded = int(round(value))
    clamped = max(-limit, min(limit, rounded))
    return clamped, clamped != rounded


async def async_calibrate(
    service: ACInfinityService,
    controller: ACInfinityController,
    reference_temperature_c: float | None,
    reference_humidity: float | None,
) -> CalibrationResult:
    """Write calibration offsets so the controller's built-in sensor reads like the reference."""
    if controller.is_ai_controller or controller.is_airtap or controller.is_room_to_room_fan:
        raise HomeAssistantError(f"{controller.controller_name} does not support calibration from Home Assistant")

    controller_id = controller.controller_id
    if not service.get_controller_setting_exists(controller_id, AdvancedSettingsKey.TEMP_UNIT):
        raise HomeAssistantError(f"Calibration settings for {controller.controller_name} have not been retrieved yet")

    result = CalibrationResult()
    settings: dict[str, int] = {}

    if reference_temperature_c is not None:
        reported_c = service.get_controller_property(controller_id, ControllerPropertyKey.TEMPERATURE)
        if reported_c is None:
            raise HomeAssistantError(f"{controller.controller_name} is not reporting a temperature")
        reported_c /= 100

        if service.get_controller_setting(controller_id, AdvancedSettingsKey.TEMP_UNIT, 0) > 0:
            current = service.get_controller_setting(controller_id, AdvancedSettingsKey.CALIBRATE_TEMP, 0)
            offset, clamped = __clamp(reference_temperature_c - (reported_c - current), TEMP_RANGE_C)
            settings |= {AdvancedSettingsKey.CALIBRATE_TEMP: offset, AdvancedSettingsKey.CALIBRATE_TEMP_F: 0}
            result.temperature_unit = UnitOfTemperature.CELSIUS
        else:
            # calibration is applied in °F; the reported value is the same reading converted from °C
            current = service.get_controller_setting(controller_id, AdvancedSettingsKey.CALIBRATE_TEMP_F, 0)
            reported_f = reported_c * 1.8 + 32
            reference_f = reference_temperature_c * 1.8 + 32
            offset, clamped = __clamp(reference_f - (reported_f - current), TEMP_RANGE_F)
            settings |= {AdvancedSettingsKey.CALIBRATE_TEMP: 0, AdvancedSettingsKey.CALIBRATE_TEMP_F: offset}
            result.temperature_unit = UnitOfTemperature.FAHRENHEIT
        result.temperature_offset = offset
        result.clamped |= clamped

    if reference_humidity is not None:
        reported = service.get_controller_property(controller_id, ControllerPropertyKey.HUMIDITY)
        if reported is None:
            raise HomeAssistantError(f"{controller.controller_name} is not reporting humidity")
        current = service.get_controller_setting(controller_id, AdvancedSettingsKey.CALIBRATE_HUMIDITY, 0)
        offset, clamped = __clamp(reference_humidity - (reported / 100 - current), HUMIDITY_RANGE)
        settings[AdvancedSettingsKey.CALIBRATE_HUMIDITY] = offset
        result.humidity_offset = offset
        result.clamped |= clamped

    if settings:
        await service.update_controller_settings(controller, settings)
    return result
