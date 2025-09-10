"""The AC Infinity integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .client import ACInfinityClient
from .const import ConfigurationKey, DEFAULT_POLLING_INTERVAL, DOMAIN, PLATFORMS, HOST
from .core import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityService,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AC Infinity from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    
    polling_interval = (
        int(entry.data[ConfigurationKey.POLLING_INTERVAL])
        if ConfigurationKey.POLLING_INTERVAL in entry.data
        else DEFAULT_POLLING_INTERVAL
    )

    service = ACInfinityService(
        ACInfinityClient(HOST, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    )

    coordinator = ACInfinityDataUpdateCoordinator(
        hass, entry, service, polling_interval
    )

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.ac_infinity.close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
