"""The AC Infinity integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_API_KEY

from .const import DOMAIN, PLATFORMS
from .ac_infinity_service import ACInfinityService

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AC Infinity from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    apiKey = entry.data[CONF_API_KEY]
    hass.data[DOMAIN][entry.entry_id] = ACInfinityService(apiKey)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
