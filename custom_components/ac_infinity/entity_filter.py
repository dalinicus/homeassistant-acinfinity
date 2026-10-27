"""Option lists for the integration wide entity filters (see core.is_excluded_by_filters)."""

from __future__ import annotations

from typing import Any

import probatio as vol

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import selector
from homeassistant.helpers.translation import async_get_translations

from . import binary_sensor, number, select, sensor, switch, time
from .const import DOMAIN, AtType, ConfigurationKey

MODE_LABELS = {
    AtType.ON: "On",
    AtType.AUTO: "Auto",
    AtType.TIMER_TO_ON: "Timer to On",
    AtType.TIMER_TO_OFF: "Timer to Off",
    AtType.CYCLE: "Cycle",
    AtType.SCHEDULE: "Schedule",
    AtType.VPD: "VPD",
    AtType.CO2: "CO2",
    AtType.CO2_FAN: "CO2 Fan",
    AtType.MOISTURE: "Moisture",
    AtType.WATER_TEMP: "Water Temp",
    AtType.PH: "pH",
    AtType.EC: "EC",
    AtType.WATER_DETECT: "Water Detect",
}


def __descriptions(module) -> list:
    found: list = []
    for name in ("CONTROLLER_DESCRIPTIONS", "SENSOR_DESCRIPTIONS", "DEVICE_DESCRIPTIONS"):
        descriptions = getattr(module, name, [])
        found.extend(descriptions.values() if isinstance(descriptions, dict) else descriptions)
    return found


def all_entity_types() -> list[tuple[str, str]]:
    """(platform, translation_key) of every kind of entity this integration can create."""
    types: set[tuple[str, str]] = {(str(Platform.FAN), "fan")}
    for platform, module in (
        (Platform.BINARY_SENSOR, binary_sensor),
        (Platform.SENSOR, sensor),
        (Platform.NUMBER, number),
        (Platform.SELECT, select),
        (Platform.SWITCH, switch),
        (Platform.TIME, time),
    ):
        types.update((str(platform), d.translation_key) for d in __descriptions(module) if d.translation_key)
    return sorted(types)


async def async_entity_type_options(hass: HomeAssistant) -> list[dict[str, str]]:
    """Selector options for every entity type, labelled with its translated name."""
    translations = await async_get_translations(hass, hass.config.language, "entity", {DOMAIN})
    options = []
    for platform, translation_key in all_entity_types():
        name = translations.get(
            f"component.{DOMAIN}.entity.{platform}.{translation_key}.name",
            translation_key.replace("_", " ").title(),
        )
        options.append({"value": f"{platform}.{translation_key}", "label": f"{name} ({platform.replace('_', ' ')})"})
    return sorted(options, key=lambda option: option["label"].lower())


def mode_options() -> list[dict[str, str]]:
    return [{"value": str(mode), "label": label} for mode, label in MODE_LABELS.items()]


async def async_filter_schema(hass: HomeAssistant, data: dict[str, Any] | None) -> vol.Schema:
    """Form for the integration wide entity filters, defaulting to the saved choices."""
    data = data or {}
    modes = mode_options()
    entity_types = await async_entity_type_options(hass)

    def saved(key: str, options: list[dict[str, str]]) -> list[str]:
        # drop saved values a later release no longer offers, or the form would fail validation
        offered = {option["value"] for option in options}
        return [value for value in data.get(key) or [] if value in offered]

    return vol.Schema({
        vol.Optional(
            ConfigurationKey.EXCLUDED_MODES, default=saved(ConfigurationKey.EXCLUDED_MODES, modes)
        ): selector({"select": {"options": modes, "multiple": True, "mode": "list"}}),
        vol.Optional(
            ConfigurationKey.EXCLUDED_ENTITY_TYPES, default=saved(ConfigurationKey.EXCLUDED_ENTITY_TYPES, entity_types)
        ): selector({"select": {"options": entity_types, "multiple": True, "mode": "dropdown"}}),
    })
