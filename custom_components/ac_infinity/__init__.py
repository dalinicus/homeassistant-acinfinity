
"""The AC Infinity integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .client import ACInfinityClient
from .const import ConfigurationKey, DEFAULT_POLLING_INTERVAL, DOMAIN, PLATFORMS, HOST, ControllerPropertyKey, \
    EntityConfigValue
from .core import (
    ACInfinityData,
    ACInfinityDeviceCoordinator,
    ACInfinityDeviceListCoordinator,
    ACInfinityEntryData,
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

    client = ACInfinityClient(HOST, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    data = ACInfinityData()
    service = ACInfinityService(client, data)

    list_coordinator = ACInfinityDeviceListCoordinator(
        hass, entry, service, polling_interval
    )
    await list_coordinator.async_config_entry_first_refresh()
    await __initialize_new_devices_if_any(hass, entry, service)

    # one device coordinator per controller; it polls mode settings/controls for that
    # controller's ports (context-driven - see ACInfinityDeviceCoordinator)
    device_coordinators = {
        controller_id: ACInfinityDeviceCoordinator(
            controller_id, hass, entry, service, polling_interval
        )
        for controller_id in data.controller_properties
    }

    await asyncio.gather(
        *(dc.async_config_entry_first_refresh() for dc in device_coordinators.values())
    )

    hass.data[DOMAIN][entry.entry_id] = ACInfinityEntryData(service, list_coordinator, device_coordinators)

    # Set up platforms with updated configuration
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def __initialize_new_devices_if_any(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    service: ACInfinityService
) -> None:
    """Add newly discovered devices to entity configuration with SensorsOnly defaults."""
    
    current_device_ids = set(service.get_device_ids() or [])
    configured_device_ids = set(entry.data[ConfigurationKey.ENTITIES].keys())
    
    # Find devices that exist in API but not in configuration
    new_device_ids = current_device_ids - configured_device_ids
    
    if not new_device_ids:
        _LOGGER.debug("No new devices found.")
        return
    
    new_data = entry.data.copy()
    entities_config = new_data[ConfigurationKey.ENTITIES].copy()
    
    for device_id in new_device_ids:
        port_count = service.get_controller_property(device_id, ControllerPropertyKey.PORT_COUNT)

        device_config = {
            "controller": EntityConfigValue.SENSORS_ONLY,
            "sensors": EntityConfigValue.SENSORS_ONLY,
        }

        for i in range(1, port_count + 1):
            device_config[f"port_{i}"] = EntityConfigValue.SENSORS_ONLY
        
        entities_config[str(device_id)] = device_config
        
        device_name = service.get_controller_property(device_id, ControllerPropertyKey.DEVICE_NAME, f"Device {device_id}")
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
        entry_data: ACInfinityEntryData = hass.data[DOMAIN][entry.entry_id]
        await entry_data.service.close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate from an old config entry version to the newest version."""
    _LOGGER.info("Migrating AC Infinity config entry from version %s", config_entry.version)

    if config_entry.version < 2:
        # Version 1 -> 2: Add entity configuration for existing devices
        new_data = config_entry.data.copy()

        service = ACInfinityService(
            ACInfinityClient(HOST, new_data[CONF_EMAIL], new_data[CONF_PASSWORD]), ACInfinityData()
        )

        try:
            await service.refresh_controllers()
            device_ids = service.get_device_ids()

            # Initialize entities configuration dictionary for v1 -> v2 migration
            new_data[ConfigurationKey.ENTITIES] = {}

            # For each device that existed in v1, create explicit configuration
            # Set to most permissive to preserve v1 behavior where all entities were enabled always
            for device_id in device_ids:
                port_count = service.get_controller_property(device_id, ControllerPropertyKey.PORT_COUNT, 0)
                device_name = service.get_controller_property(device_id, ControllerPropertyKey.DEVICE_NAME, f"Device {device_id}")

                device_config = {
                    "controller": EntityConfigValue.SENSORS_AND_SETTINGS,
                    "sensors": EntityConfigValue.SENSORS_ONLY,
                }

                for i in range(1, port_count + 1):
                    device_config[f"port_{i}"] = EntityConfigValue.ALL

                new_data[ConfigurationKey.ENTITIES][str(device_id)] = device_config

                _LOGGER.info(
                    "Migrated device '%s' (ID: %s) to v2 with all entities enabled to preserve v1 behavior",
                    device_name, device_id
                )

            new_data[ConfigurationKey.MODIFIED_AT] = datetime.now().isoformat()

            hass.config_entries.async_update_entry(
                config_entry,
                data=new_data,
                version=2
            )
        except Exception as ex:
            _LOGGER.error("Failed to migrate config entry from v1 to v2: %s", ex)
            return False
        finally:
            await service.close()

        _LOGGER.info("Successfully migrated config entry from version 1 to version 2")

    return True
