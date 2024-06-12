"""The AC Infinity integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL, DOMAIN, PLATFORMS
from .core import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityService,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AC Infinity from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    polling_interval = (
        int(entry.data[CONF_POLLING_INTERVAL])
        if CONF_POLLING_INTERVAL in entry.data
        else DEFAULT_POLLING_INTERVAL
    )

    service = ACInfinityService(entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    coordinator = ACInfinityDataUpdateCoordinator(hass, service, polling_interval)

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
