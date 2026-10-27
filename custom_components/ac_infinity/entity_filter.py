"""Option lists for the integration wide entity filters (see core.is_excluded_by_filters)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import probatio as vol

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import selector
from homeassistant.helpers.translation import async_get_translations

from . import binary_sensor, number, select, sensor, switch, time
from .const import DOMAIN, AtType, ConfigurationKey

MODE_LABELS = {
    AtType.OFF: "Off",
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


async def async_entity_type_options(hass: HomeAssistant, only: set[str] | None = None) -> list[dict[str, str]]:
    """Selector options for entity types (all, or only the given "platform.translation_key" values), labelled with
    their translated names."""
    translations = await async_get_translations(hass, hass.config.language, "entity", {DOMAIN})
    options = []
    for platform, translation_key in all_entity_types():
        value = f"{platform}.{translation_key}"
        if only is not None and value not in only:
            continue
        name = translations.get(
            f"component.{DOMAIN}.entity.{platform}.{translation_key}.name",
            translation_key.replace("_", " ").title(),
        )
        options.append({"value": value, "label": f"{name} ({platform.replace('_', ' ')})"})
    return sorted(options, key=lambda option: option["label"].lower())


def mode_options() -> list[dict[str, str]]:
    return [{"value": str(mode), "label": label} for mode, label in MODE_LABELS.items()]


async def async_keep_list_schema(
    hass: HomeAssistant,
    filters: Mapping[str, Any] | None,
    entity_types: set[str] | None = None,
    select_all: bool = False,
) -> vol.Schema:
    """Form for one controller's keep-list: tick the entity types to keep, everything else is removed.

    entity_types limits the list to what the controller supports (None lists every type).  Nothing is ticked
    until the user ticks it, unless select_all is set, which ticks every listed type so a few can be unticked."""
    filters = filters or {}
    type_options = await async_entity_type_options(hass, entity_types)
    offered = {option["value"] for option in type_options}
    if select_all:
        ticked = sorted(offered)
    else:
        # drop saved values no longer offered, or the form would fail validation
        ticked = [value for value in filters.get(ConfigurationKey.INCLUDED_ENTITY_TYPES) or [] if value in offered]

    return vol.Schema({
        vol.Optional(ConfigurationKey.SELECT_ALL_ENTITY_TYPES, default=False): bool,
        vol.Optional(ConfigurationKey.INCLUDED_ENTITY_TYPES, default=ticked): selector(
            {"select": {"options": type_options, "multiple": True, "mode": "list"}}
        ),
    })
