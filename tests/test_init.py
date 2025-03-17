import asyncio
from asyncio import Future
from types import MappingProxyType
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util.hass_dict import HassDict
from pytest_mock import MockFixture

from custom_components.ac_infinity import (
    ACInfinityDataUpdateCoordinator,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.ac_infinity.client import ACInfinityClient
from custom_components.ac_infinity.const import DOMAIN, PLATFORMS
from custom_components.ac_infinity.core import ACInfinityService

EMAIL = "myemail@unittest.com"
PASSWORD = "hunter2"
ENTRY_ID = f"ac_infinity-{EMAIL}"


@pytest.fixture
def setup(mocker: MockFixture):
    future: Future = asyncio.Future()
    future.set_result(None)

    bool_future: Future = asyncio.Future()
    bool_future.set_result(True)

    mocker.patch.object(ACInfinityService, "refresh", return_value=future)
    mocker.patch.object(ACInfinityClient, "__init__", return_value=None)
    mocker.patch.object(HomeAssistant, "__init__", return_value=None)
    mocker.patch.object(ConfigEntries, "__init__", return_value=None)
    mocker.patch.object(
        ConfigEntries, "async_forward_entry_setups", return_value=future
    )
    mocker.patch.object(
        ConfigEntries, "async_unload_platforms", return_value=bool_future
    )

    config_entry = ConfigEntry(
        entry_id=ENTRY_ID,
        data={CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD},
        domain=DOMAIN,
        minor_version=0,
        source="",
        title="",
        version=0,
        options=None,
        unique_id=None,
        discovery_keys=MappingProxyType({}),
        state=ConfigEntryState.SETUP_IN_PROGRESS,
        subentries_data=None,
    )

    hass = HomeAssistant("/path")
    hass.config_entries = ConfigEntries(hass, {})
    hass.data = HassDict({})

    return hass, config_entry


@pytest.mark.asyncio
class TestInit:
    async def test_async_setup_entry_ac_infinity_init(self, setup):
        """when setting up, ac_infinity should be initialized and assigned to the hass object"""
        (hass, config_entry) = setup
        await async_setup_entry(hass, config_entry)

        assert hass.data[DOMAIN][ENTRY_ID] is not None

    async def test_async_setup_entry_platforms_initialized(self, setup):
        """When setting up, all platforms should be initialized"""
        hass: HomeAssistant
        (hass, config_entry) = setup

        result = await async_setup_entry(hass, config_entry)

        assert result

        assert isinstance(hass.config_entries.async_forward_entry_setups, AsyncMock)
        hass.config_entries.async_forward_entry_setups.assert_called_with(
            config_entry, PLATFORMS
        )

    async def test_async_unload_entry(self, setup):
        """When unloading, all platforms should be unloaded"""
        hass: HomeAssistant
        (hass, config_entry) = setup
        hass.data = HassDict({DOMAIN: {ENTRY_ID: ACInfinityService(EMAIL, PASSWORD)}})
        result = await async_unload_entry(hass, config_entry)

        assert result

        assert isinstance(hass.config_entries.async_unload_platforms, AsyncMock)
        hass.config_entries.async_unload_platforms.assert_called_with(
            config_entry, PLATFORMS
        )

    async def test_update_update_failed_thrown(self, mocker: MockFixture, setup):
        (hass, config_entry) = setup

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        mocker.patch.object(ac_infinity, "refresh", side_effect=Exception("unit test"))
        coordinator = ACInfinityDataUpdateCoordinator(
            hass, config_entry, ac_infinity, 10
        )
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
