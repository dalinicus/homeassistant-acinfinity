"""The AC Infinity integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Tuple

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .ac_infinity import ACInfinity, ACInfinityDevice, ACInfinityDevicePort
from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AC Infinity from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    ac_infinity = ACInfinity(entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    coordinator = ACInfinityDataUpdateCoordinator(hass, ac_infinity)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class ACInfinityEntity(CoordinatorEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        data_key: str,
    ):
        super().__init__(coordinator)
        self._data_key = data_key


class ACInfinityDeviceEntity(ACInfinityEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        data_key: str,
        label: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, data_key)
        self._device = device

        self._attr_icon = icon
        self._attr_device_info = device.device_info
        self._attr_unique_id = f"{DOMAIN}_{device.mac_addr}_{data_key}"
        self._attr_name = f"{device.device_name} {label}"

    def get_property_value(self):
        coordinator: ACInfinityDataUpdateCoordinator = self.coordinator
        return coordinator.ac_infinity.get_device_property(
            self._device.device_id, self._data_key
        )


class ACInfinityPortEntity(ACInfinityEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        data_key: str,
        label: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, data_key)
        self._device = device
        self._port = port

        self._attr_icon = icon
        self._attr_device_info = port.device_info
        self._attr_name = f"{device.device_name} {port.port_name} {label}"
        self._attr_unique_id = (
            f"{DOMAIN}_{device.mac_addr}_port_{port.port_id}_{data_key}"
        )


class ACInfinityPortPropertyEntity(ACInfinityPortEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        data_key: str,
        label: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, device, port, data_key, label, icon)

    def get_property_value(self):
        coordinator: ACInfinityDataUpdateCoordinator = self.coordinator
        return coordinator.ac_infinity.get_device_port_property(
            self._device.device_id, self._port.port_id, self._data_key
        )


class ACInfinityPortSettingEntity(ACInfinityPortEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        data_key: str,
        label: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, device, port, data_key, label, icon)

    def get_setting_value(self, default=None) -> int:
        coordinator: ACInfinityDataUpdateCoordinator = self.coordinator
        return coordinator.ac_infinity.get_device_port_setting(
            self._device.device_id, self._port.port_id, self._data_key, default
        )

    async def set_setting_value(self, value: int) -> None:
        coordinator: ACInfinityDataUpdateCoordinator = self.coordinator
        await coordinator.ac_infinity.set_device_port_setting(
            self._device.device_id, self._port.port_id, self._data_key, value
        )
        await coordinator.async_request_refresh()


class ACInfinityPortTupleSettingEntity(ACInfinityPortEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        tuple_key: Tuple[str, str],
        label: str,
        icon: str,
    ) -> None:
        """The first tuple value will be used as the "primary" data key used for ids.
        Values will be fetched from api using both keys.
        """
        (leftKey, _) = tuple_key
        super().__init__(coordinator, device, port, leftKey, label, icon)
        self._tuple_key = tuple_key

    def get_setting_value(self, default=None) -> Tuple[int, int]:
        coordinator: ACInfinityDataUpdateCoordinator = self.coordinator

        (leftKey, rightKey) = self._tuple_key
        leftValue = coordinator.ac_infinity.get_device_port_setting(
            self._device.device_id, self._port.port_id, leftKey, default
        )
        rightValue = coordinator.ac_infinity.get_device_port_setting(
            self._device.device_id, self._port.port_id, rightKey, default
        )

        return (leftValue, rightValue)

    async def set_setting_value(self, value: Tuple[int, int]) -> None:
        coordinator: ACInfinityDataUpdateCoordinator = self.coordinator

        (leftKey, rightKey) = self._tuple_key
        (leftValue, rightValue) = value
        await coordinator.ac_infinity.set_device_port_settings(
            self._device.device_id,
            self._port.port_id,
            [(leftKey, leftValue), (rightKey, rightValue)],
        )

        await coordinator.async_request_refresh()


class ACInfinityDataUpdateCoordinator(DataUpdateCoordinator):
    """Handles updating data for the integration"""

    def __init__(self, hass, ac_infinity: ACInfinity):
        """Constructor"""
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=10)
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
