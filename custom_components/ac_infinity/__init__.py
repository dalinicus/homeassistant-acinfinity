"""The AC Infinity integration."""
from __future__ import annotations

import abc
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Awaitable

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .ac_infinity import ACInfinity, ACInfinityController, ACInfinityPort
from .const import CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AC Infinity from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    polling_interval = (
        int(entry.data[CONF_POLLING_INTERVAL])
        if CONF_POLLING_INTERVAL in entry.data
        else DEFAULT_POLLING_INTERVAL
    )

    ac_infinity = ACInfinity(entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    coordinator = ACInfinityDataUpdateCoordinator(hass, ac_infinity, polling_interval)

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


@dataclass
class ACInfinityControllerReadOnlyMixin:
    """Mixin for adding values for controller level sensors"""

    get_value_fn: Callable[[ACInfinity, ACInfinityController], StateType]
    """Input data object and a device id; output the value."""


@dataclass
class ACInfinityPortReadOnlyMixin:
    """Mixin for adding values for port device level sensors"""

    get_value_fn: Callable[[ACInfinity, ACInfinityPort], StateType]
    """Input data object, device id, and port number; output the value."""


@dataclass
class ACInfinityPortReadWriteMixin(ACInfinityPortReadOnlyMixin):
    """Mixin for adding values for port device level sensors"""

    set_value_fn: Callable[[ACInfinity, ACInfinityPort, StateType], Awaitable[None]]
    """Input data object, device id, port number, and desired value."""


class ACInfinityDataUpdateCoordinator(DataUpdateCoordinator):
    """Handles updating data for the integration"""

    def __init__(self, hass, ac_infinity: ACInfinity, polling_interval: int):
        """Constructor"""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=polling_interval),
        )

        self._ac_infinity = ac_infinity

    async def _async_update_data(self):
        """Fetch data from the AC Infinity API"""
        _LOGGER.debug("Refreshing data from data update coordinator")
        try:
            async with async_timeout.timeout(10):
                await self._ac_infinity.update()
                return self._ac_infinity
        except Exception as e:
            _LOGGER.error("Unable to refresh from data update coordinator", exc_info=e)
            raise UpdateFailed from e

    @property
    def ac_infinity(self) -> ACInfinity:
        return self._ac_infinity


class ACInfinityEntity(CoordinatorEntity[ACInfinityDataUpdateCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        data_key: str,
    ):
        super().__init__(coordinator)
        self._data_key = data_key

    @property
    def ac_infinity(self) -> ACInfinity:
        """Returns the underlying ac_infinity api object from the assigned coordinator"""
        return self.coordinator.ac_infinity

    @abc.abstractproperty
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""

    @abc.abstractproperty
    def device_info(self) -> DeviceInfo:
        """Returns the device info for the controller entity"""


class ACInfinityControllerEntity(ACInfinityEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        controller: ACInfinityController,
        data_key: str,
    ):
        super().__init__(coordinator, data_key)
        self._controller = controller

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""
        return f"{DOMAIN}_{self._controller.mac_addr}_{self._data_key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Returns the device info for the controller entity"""
        return self._controller.device_info

    @property
    def controller(self) -> ACInfinityController:
        return self._controller


class ACInfinityPortEntity(ACInfinityEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        port: ACInfinityPort,
        data_key: str,
    ):
        super().__init__(coordinator, data_key)
        self._port = port

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""
        return f"{DOMAIN}_{self._port.parent_mac_addr}_port_{self._port.port_id}_{self._data_key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Returns the device info for the port entity"""
        return self._port.device_info

    @property
    def port(self) -> ACInfinityPort:
        return self._port
