import asyncio
from asyncio import Future

import pytest
from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_mock import MockFixture

from custom_components.ac_infinity import (
    ACInfinityDataUpdateCoordinator,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.ac_infinity.ac_infinity import ACInfinity
from custom_components.ac_infinity.client import ACInfinityClient
from custom_components.ac_infinity.const import DOMAIN, PLATFORMS

EMAIL = "myemail@unittest.com"
PASSWORD = "hunter2"
ENTRY_ID = f"ac_infinity-{EMAIL}"


@pytest.fixture
def setup(mocker: MockFixture):
    future: Future = asyncio.Future()
    future.set_result(None)

    boolFuture: Future = asyncio.Future()
    boolFuture.set_result(True)

    mocker.patch.object(ACInfinity, "update", return_value=future)
    mocker.patch.object(ACInfinityClient, "__init__", return_value=None)
    mocker.patch.object(HomeAssistant, "__init__", return_value=None)
    mocker.patch.object(ConfigEntry, "__init__", return_value=None)
    mocker.patch.object(ConfigEntries, "__init__", return_value=None)
    mocker.patch.object(
        ConfigEntries, "async_forward_entry_setups", return_value=future
    )
    mocker.patch.object(
        ConfigEntries, "async_unload_platforms", return_value=boolFuture
    )

    config_entry = ConfigEntry()
    config_entry.entry_id = ENTRY_ID
    config_entry.data = {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}

    hass = HomeAssistant("/path")
    hass.config_entries = ConfigEntries()
    hass.data = {}

    return (hass, config_entry)


@pytest.mark.asyncio
class TestInit:
    async def test_async_setup_entry_aerogarden_init(self, setup):
        """when setting up, aerogarden should be initialized and assigned to the hass object"""
        (hass, config_entry) = setup

        await async_setup_entry(hass, config_entry)

        assert hass.data[DOMAIN][ENTRY_ID] is not None

    async def test_async_setup_entry_platforms_initalized(self, setup):
        """When setting up, all platforms should be initialized"""
        hass: HomeAssistant
        (hass, config_entry) = setup

        result = await async_setup_entry(hass, config_entry)

        assert result
        hass.config_entries.async_forward_entry_setups.assert_called_with(
            config_entry, PLATFORMS
        )

    async def test_async_unload_entry(self, setup):
        """When unloading, all platforms should be unloaded"""
        hass: HomeAssistant
        (hass, config_entry) = setup
        hass.data = {DOMAIN: {ENTRY_ID: ACInfinity(EMAIL, PASSWORD)}}
        result = await async_unload_entry(hass, config_entry)

        assert result
        hass.config_entries.async_unload_platforms.assert_called_with(
            config_entry, PLATFORMS
        )

    async def test_update_update_failed_thrown(self, mocker: MockFixture, setup):
        (hass, _) = setup

        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        mocker.patch.object(ac_infinity, "update", side_effect=Exception("unit test"))
        coordinator = ACInfinityDataUpdateCoordinator(hass, ac_infinity)
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
