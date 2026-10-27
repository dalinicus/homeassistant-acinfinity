"""Diagnostics support for AC Infinity."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .core import ACInfinityEntryData

# identifiers that tie a payload to an account, a physical device, or a home
TO_REDACT = {
    CONF_EMAIL,
    CONF_PASSWORD,
    "appEmail",
    "devMacAddr",
    "devCode",
    "wifiName",
    "zoneId",
    "uuid",
    "token",
}


def _by_key(cache: dict[tuple, Any]) -> dict[str, Any]:
    """Cache keys are tuples (controller id, port[, sensor type]); json needs string keys."""
    return {"_".join(str(part) for part in key): value for key, value in cache.items()}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry: the raw API payloads the integration last cached."""
    entry_data: ACInfinityEntryData = hass.data[DOMAIN][entry.entry_id]
    data = entry_data.service.data

    return async_redact_data(
        {
            "entry": entry.data,
            "controller_properties": data.controller_properties,
            "sensor_properties": _by_key(data.sensor_properties),
            "device_properties": _by_key(data.device_properties),
            "device_controls": _by_key(data.device_controls),
            "device_settings": _by_key(data.device_settings),
        },
        TO_REDACT,
    )
