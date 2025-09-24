
"""The AC Infinity integration."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .client import ACInfinityClient
from .const import ConfigurationKey, DEFAULT_POLLING_INTERVAL, DOMAIN, PLATFORMS, HOST, ControllerPropertyKey, \
    EntityConfigValue
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
    await __initialize_new_devices_if_any(hass, entry, coordinator.ac_infinity)
    
    # Set up platforms with updated configuration
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def __initialize_new_devices_if_any(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    ac_infinity: ACInfinityService
) -> None:
    """Add newly discovered devices to entity configuration with SensorsOnly defaults."""
    
    current_device_ids = set(ac_infinity.get_device_ids() or [])
    configured_device_ids = set(entry.data[ConfigurationKey.ENTITIES].keys())
    
    # Find devices that exist in API but not in configuration
    new_device_ids = current_device_ids - configured_device_ids
    
    if not new_device_ids:
        _LOGGER.debug("No new devices found.")
        return
    
    new_data = entry.data.copy()
    entities_config = new_data[ConfigurationKey.ENTITIES].copy()
    
    for device_id in new_device_ids:
        port_count = ac_infinity.get_controller_property(device_id, ControllerPropertyKey.PORT_COUNT)

        device_config = {
            "controller": EntityConfigValue.SensorsOnly,
            "sensors": EntityConfigValue.SensorsOnly,
        }

        for i in range(1, port_count + 1):
            device_config[f"port_{i}"] = EntityConfigValue.SensorsOnly
        
        entities_config[str(device_id)] = device_config
        
        device_name = ac_infinity.get_controller_property(device_id, ControllerPropertyKey.DEVICE_NAME, f"Device {device_id}")
        _LOGGER.info(
            "Added new device '%s' (ID: %s) to entity configuration with SensorsOnly defaults", 
            device_name, device_id
        )
    
    new_data[ConfigurationKey.ENTITIES] = entities_config
    new_data[ConfigurationKey.MODIFIED_AT] = datetime.now().isoformat()
    
    hass.config_entries.async_update_entry(entry, data=new_data)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.ac_infinity.close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate from an old config entry version to the newest version."""
    _LOGGER.info("Migrating AC Infinity config entry from version %s", config_entry.version)

    if config_entry.version < 2:
        # Version 1 -> 2: Add entity configuration for existing devices
        new_data = config_entry.data.copy()

        ac_infinity = ACInfinityService(
            ACInfinityClient(HOST, new_data[CONF_EMAIL], new_data[CONF_PASSWORD])
        )

        try:
            await ac_infinity.refresh()
            device_ids = ac_infinity.get_device_ids()

            # Initialize entities configuration dictionary for v1 -> v2 migration
            new_data[ConfigurationKey.ENTITIES] = {}

            # For each device that existed in v1, create explicit configuration
            # Set to most permissive to preserve v1 behavior where all entities were enabled always
            for device_id in device_ids:
                port_count = ac_infinity.get_controller_property(device_id, ControllerPropertyKey.PORT_COUNT, 0)
                device_name = ac_infinity.get_controller_property(device_id, ControllerPropertyKey.DEVICE_NAME, f"Device {device_id}")

                device_config = {
                    "controller": EntityConfigValue.SensorsAndSettings,
                    "sensors": EntityConfigValue.SensorsOnly,
                }

                for i in range(1, port_count + 1):
                    device_config[f"port_{i}"] = EntityConfigValue.All

                new_data[ConfigurationKey.ENTITIES][str(device_id)] = device_config

                _LOGGER.info(
                    "Migrated device '%s' (ID: %s) to v2 with all entities enabled to preserve v1 behavior",
                    device_name, device_id
                )

        except Exception as ex:
            _LOGGER.error("Failed to migrate config entry from v1 to v2: %s", ex)
            return False
        finally:
            await ac_infinity.close()

        new_data[ConfigurationKey.MODIFIED_AT] = datetime.now().isoformat()

        hass.config_entries.async_update_entry(
            config_entry, 
            data=new_data, 
            version=2
        )
        
        _LOGGER.info("Successfully migrated config entry from version 1 to version 2")

    return True
