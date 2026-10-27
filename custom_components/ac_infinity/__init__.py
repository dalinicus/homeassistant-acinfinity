
"""The AC Infinity integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import probatio as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr, entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .calibration import async_calibrate, read_reference

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

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_CALIBRATE = "calibrate"
ATTR_DEVICE_ID = "device_id"
ATTR_TEMPERATURE_ENTITY = "temperature_entity"
ATTR_HUMIDITY_ENTITY = "humidity_entity"

CALIBRATE_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): cv.string,
    vol.Optional(ATTR_TEMPERATURE_ENTITY): cv.entity_id,
    vol.Optional(ATTR_HUMIDITY_ENTITY): cv.entity_id,
})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration's actions."""

    async def async_handle_calibrate(call: ServiceCall) -> ServiceResponse:
        temperature_entity = call.data.get(ATTR_TEMPERATURE_ENTITY)
        humidity_entity = call.data.get(ATTR_HUMIDITY_ENTITY)
        if not temperature_entity and not humidity_entity:
            raise HomeAssistantError("Choose a reference temperature and/or humidity sensor")

        device = dr.async_get(hass).async_get(call.data[ATTR_DEVICE_ID])
        controller_ids = {identifier[1] for identifier in device.identifiers if identifier[0] == DOMAIN} if device else set()
        for entry_data in hass.data.get(DOMAIN, {}).values():
            controller = next(
                (c for c in entry_data.service.get_all_controller_properties() if c.controller_id in controller_ids),
                None,
            )
            if controller is None:
                continue

            result = await async_calibrate(
                entry_data.service,
                controller,
                read_reference(hass, temperature_entity, temperature=True) if temperature_entity else None,
                read_reference(hass, humidity_entity, temperature=False) if humidity_entity else None,
            )
            await entry_data.list_coordinator.async_request_refresh()
            return {
                "temperature_offset": result.temperature_offset,
                "temperature_unit": result.temperature_unit,
                "humidity_offset": result.humidity_offset,
                "clamped": result.clamped,
            }

        raise HomeAssistantError("Select an AC Infinity controller device")

    hass.services.async_register(
        DOMAIN,
        SERVICE_CALIBRATE,
        async_handle_calibrate,
        schema=CALIBRATE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


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
    try:
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
    except Exception:
        # setup is retried with a fresh client; don't leak this one's http session
        await service.close()
        raise

    hass.data[DOMAIN][entry.entry_id] = ACInfinityEntryData(service, list_coordinator, device_coordinators)

    # Set up platforms with updated configuration
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    __remove_excluded_entities_and_empty_devices(hass, entry, hass.data[DOMAIN][entry.entry_id])

    return True


def __current_device_identifiers(service: ACInfinityService) -> set[tuple[str, str]]:
    """Registry identifiers of every controller, port and sensor device the account currently has."""
    identifiers: set[tuple[str, str]] = set()
    for controller in service.get_all_controller_properties():
        identifiers.add(controller.identifier)
        for child in (*controller.devices, *controller.sensors):
            identifiers |= child.device_info.get("identifiers", set())
    return identifiers


def __remove_excluded_entities_and_empty_devices(
    hass: HomeAssistant, entry: ConfigEntry, entry_data: ACInfinityEntryData
) -> None:
    """Remove registry entries for entities the user excluded (entity filters, or disabled in the per-device
    options), and port/sensor devices left without any entities.  Without this, they linger as "unavailable".

    Only deliberate exclusions are removed.  An entity that is merely missing from the API's data on this load
    (an offline controller, a partial response) keeps its registry entry, name and area."""
    entity_registry = er.async_get(hass)
    removed = 0
    for registry_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if registry_entry.unique_id in entry_data.excluded_unique_ids:
            entity_registry.async_remove(registry_entry.entity_id)
            removed += 1

    device_registry = dr.async_get(hass)
    controller_identifiers = {(DOMAIN, controller_id) for controller_id in entry_data.service.get_device_ids()}
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        if device.identifiers & controller_identifiers:
            continue
        if not er.async_entries_for_device(entity_registry, device.id, include_disabled_entities=True):
            device_registry.async_update_device(device.id, remove_config_entry_id=entry.entry_id)

    if removed:
        _LOGGER.info("Removed %s AC Infinity entities excluded in the integration options", removed)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Allow a device to be deleted from the UI only if the account no longer has it."""
    entry_data: ACInfinityEntryData | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if entry_data is None:
        return True
    return not device.identifiers & __current_device_identifiers(entry_data.service)


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
        device_config = {
            "controller": EntityConfigValue.SENSORS_ONLY,
            "sensors": EntityConfigValue.SENSORS_ONLY,
        }

        for i in service.get_device_ports(device_id):
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
                device_name = service.get_controller_property(device_id, ControllerPropertyKey.DEVICE_NAME, f"Device {device_id}")

                device_config = {
                    "controller": EntityConfigValue.SENSORS_AND_SETTINGS,
                    "sensors": EntityConfigValue.SENSORS_ONLY,
                }

                for i in service.get_device_ports(device_id):
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
