import asyncio
from copy import deepcopy
from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.util.hass_dict import HassDict
from pytest_mock import MockFixture

from custom_components.ac_infinity import (
    async_migrate_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.ac_infinity.client import ACInfinityClient
from custom_components.ac_infinity.const import (
    DOMAIN,
    PLATFORMS,
    ConfigurationKey,
    EntityConfigValue,
    ControllerPropertyKey
)
from custom_components.ac_infinity.core import (
    ACInfinityData,
    ACInfinityDeviceCoordinator,
    ACInfinityDeviceListCoordinator,
    ACInfinityEntryData,
    ACInfinityService,
)
from tests import HOST, CONFIG_ENTRY_DATA
from tests.data_models import (
    DEVICE_ID,
    AI_DEVICE_ID,
    CONTROLLER_PROPERTIES_DATA,
    DEVICE_CONTROLS,
    DEVICE_INFO_LIST_ALL,
)

EMAIL = "myemail@unittest.com"
PASSWORD = "hunter2"
ENTRY_ID = f"ac_infinity-{EMAIL}"


@pytest.fixture
def setup(mocker: MockFixture):
    mocker.patch.object(ACInfinityClient, "login", new_callable=AsyncMock)
    mocker.patch.object(
        ACInfinityClient,
        "get_account_controllers",
        new_callable=AsyncMock,
        return_value=deepcopy(DEVICE_INFO_LIST_ALL),
    )
    mocker.patch.object(
        ACInfinityClient,
        "get_device_mode_settings",
        new_callable=AsyncMock,
        return_value=deepcopy(DEVICE_CONTROLS),
    )
    mocker.patch.object(ACInfinityClient, "close", new_callable=AsyncMock)
    mocker.patch.object(HomeAssistant, "__init__", return_value=None)
    mocker.patch.object(ConfigEntries, "__init__", return_value=None)
    mocker.patch.object(
        ConfigEntries, "async_forward_entry_setups", new_callable=AsyncMock
    )
    mocker.patch.object(
        ConfigEntries, "async_unload_platforms", new_callable=AsyncMock, return_value=True
    )

    config_entry = ConfigEntry(
        entry_id=ENTRY_ID,
        data=deepcopy(CONFIG_ENTRY_DATA),
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
        """when setting up, an ACInfinityEntryData should be initialized and assigned to the hass object"""
        (hass, config_entry) = setup
        await async_setup_entry(hass, config_entry)

        entry_data = hass.data[DOMAIN][ENTRY_ID]
        assert isinstance(entry_data, ACInfinityEntryData)
        assert isinstance(entry_data.service, ACInfinityService)
        assert isinstance(entry_data.list_coordinator, ACInfinityDeviceListCoordinator)
        assert set(entry_data.device_coordinators.keys()) == {
            str(DEVICE_ID),
            str(AI_DEVICE_ID),
        }
        for device_coordinator in entry_data.device_coordinators.values():
            assert isinstance(device_coordinator, ACInfinityDeviceCoordinator)

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
        """When unloading, all platforms should be unloaded and the service closed"""
        hass: HomeAssistant
        (hass, config_entry) = setup

        await async_setup_entry(hass, config_entry)
        entry_data: ACInfinityEntryData = hass.data[DOMAIN][ENTRY_ID]
        close_mock = AsyncMock()
        entry_data.service.close = close_mock

        result = await async_unload_entry(hass, config_entry)

        assert result

        assert isinstance(hass.config_entries.async_unload_platforms, AsyncMock)
        hass.config_entries.async_unload_platforms.assert_called_with(
            config_entry, PLATFORMS
        )
        close_mock.assert_called_once()
        assert ENTRY_ID not in hass.data[DOMAIN]

    async def test_async_migrate_entry_version_1_to_2_success(self, mocker: MockFixture):
        """Test successful migration from version 1 to version 2"""
        # Create a version 1 config entry (without entity configuration)
        v1_config_entry = ConfigEntry(
            entry_id=ENTRY_ID,
            data={
                CONF_EMAIL: EMAIL,
                CONF_PASSWORD: PASSWORD,
            },
            domain=DOMAIN,
            minor_version=0,
            source="",
            title="",
            version=1,  # Version 1
            options=None,
            unique_id=None,
            discovery_keys=MappingProxyType({}),
            state=ConfigEntryState.SETUP_IN_PROGRESS,
            subentries_data=None,
        )

        hass = HomeAssistant("/path")
        hass.config_entries = ConfigEntries(hass, {})

        # Create a real ACInfinityService instance with mocked client
        mock_client = MagicMock()
        mock_ac_infinity = ACInfinityService(mock_client, ACInfinityData())
        mock_ac_infinity.refresh_controllers = AsyncMock()
        mock_ac_infinity.close = AsyncMock()

        # Set up the service's cached data like the real service would after a refresh
        mock_ac_infinity.data.controller_properties = deepcopy(CONTROLLER_PROPERTIES_DATA)

        # Mock the get_device_ids method to return our test device IDs
        mock_ac_infinity.get_device_ids = MagicMock(return_value=[DEVICE_ID, AI_DEVICE_ID])

        # Mock ACInfinityService constructor
        mocker.patch.object(ACInfinityClient, "__init__", return_value=None)

        # Mock the service instance creation to return our mock
        mocker.patch("custom_components.ac_infinity.ACInfinityService", return_value=mock_ac_infinity)

        # Mock async_update_entry
        mock_update_entry = mocker.patch.object(hass.config_entries, "async_update_entry")

        # Execute the migration
        result = await async_migrate_entry(hass, v1_config_entry)

        # Verify migration was successful
        assert result is True

        # Verify async_update_entry was called
        mock_update_entry.assert_called_once()

        # Get the call arguments
        call_args = mock_update_entry.call_args
        updated_entry = call_args[0][0]  # First positional argument

        # Verify the entry is the same object
        assert updated_entry is v1_config_entry

        # Verify the data and version were updated
        update_kwargs = call_args[1]  # Keyword arguments
        assert "data" in update_kwargs
        assert "version" in update_kwargs
        assert update_kwargs["version"] == 2

        # Verify the new data structure
        new_data = update_kwargs["data"]
        assert ConfigurationKey.ENTITIES in new_data
        assert ConfigurationKey.MODIFIED_AT in new_data

        # Verify entity configuration for both devices
        entities_config = new_data[ConfigurationKey.ENTITIES]
        assert str(DEVICE_ID) in entities_config
        assert str(AI_DEVICE_ID) in entities_config

        # Verify device configuration structure
        for device_id in [DEVICE_ID, AI_DEVICE_ID]:
            device_config = entities_config[str(device_id)]
            assert device_config["controller"] == EntityConfigValue.SENSORS_AND_SETTINGS
            assert device_config["sensors"] == EntityConfigValue.SENSORS_ONLY
            assert device_config["port_1"] == EntityConfigValue.ALL
            assert device_config["port_2"] == EntityConfigValue.ALL
            assert device_config["port_3"] == EntityConfigValue.ALL
            assert device_config["port_4"] == EntityConfigValue.ALL

        # Verify service methods were called
        mock_ac_infinity.refresh_controllers.assert_called_once()
        mock_ac_infinity.get_device_ids.assert_called_once()
        mock_ac_infinity.close.assert_called_once()

    async def test_async_migrate_entry_version_1_api_failure(self, mocker: MockFixture):
        """Test migration failure when API call fails"""
        # Create a version 1 config entry
        v1_config_entry = ConfigEntry(
            entry_id=ENTRY_ID,
            data={
                CONF_EMAIL: EMAIL,
                CONF_PASSWORD: PASSWORD,
            },
            domain=DOMAIN,
            minor_version=0,
            source="",
            title="",
            version=1,
            options=None,
            unique_id=None,
            discovery_keys=MappingProxyType({}),
            state=ConfigEntryState.SETUP_IN_PROGRESS,
            subentries_data=None,
        )

        hass = HomeAssistant("/path")
        hass.config_entries = ConfigEntries(hass, {})

        # Mock the AC Infinity service to fail on refresh
        mock_ac_infinity = MagicMock()
        mock_ac_infinity.refresh_controllers = AsyncMock(side_effect=Exception("API Error"))
        mock_ac_infinity.close = AsyncMock()

        # Mock service creation
        mocker.patch.object(ACInfinityClient, "__init__", return_value=None)
        mocker.patch("custom_components.ac_infinity.ACInfinityService", return_value=mock_ac_infinity)

        # Mock async_update_entry (should not be called on failure)
        mock_update_entry = mocker.patch.object(hass.config_entries, "async_update_entry")

        # Execute the migration
        result = await async_migrate_entry(hass, v1_config_entry)

        # Verify migration failed
        assert result is False

        # Verify async_update_entry was not called
        mock_update_entry.assert_not_called()

        # Verify close was still called in finally block
        mock_ac_infinity.close.assert_called_once()

    async def test_async_migrate_entry_version_2_no_migration_needed(self, mocker: MockFixture):
        """Test that version 2 entries are not migrated"""
        # Create a version 2 config entry (current version)
        v2_config_entry = ConfigEntry(
            entry_id=ENTRY_ID,
            data=deepcopy(CONFIG_ENTRY_DATA),  # Already has entity configuration
            domain=DOMAIN,
            minor_version=0,
            source="",
            title="",
            version=2,  # Current version
            options=None,
            unique_id=None,
            discovery_keys=MappingProxyType({}),
            state=ConfigEntryState.SETUP_IN_PROGRESS,
            subentries_data=None,
        )

        hass = HomeAssistant("/path")
        hass.config_entries = ConfigEntries(hass, {})

        # Mock async_update_entry (should not be called)
        mock_update_entry = mocker.patch.object(hass.config_entries, "async_update_entry")

        # Execute the migration
        result = await async_migrate_entry(hass, v2_config_entry)

        # Verify migration was successful (no-op)
        assert result is True

        # Verify async_update_entry was not called
        mock_update_entry.assert_not_called()

    async def test_initialize_new_devices_multiple_new_devices(self, mocker: MockFixture):
        """Test adding multiple new devices with different port counts during setup"""
        # Create a config entry with no existing devices
        empty_data = deepcopy(CONFIG_ENTRY_DATA)
        empty_data[ConfigurationKey.ENTITIES] = {}

        config_entry = ConfigEntry(
            entry_id=ENTRY_ID,
            data=empty_data,
            domain=DOMAIN,
            minor_version=0,
            source="",
            title="",
            version=2,
            options=None,
            unique_id=None,
            discovery_keys=MappingProxyType({}),
            state=ConfigEntryState.SETUP_IN_PROGRESS,
            subentries_data=None,
        )

        hass = HomeAssistant("/path")
        hass.config_entries = ConfigEntries(hass, {})
        hass.data = HassDict({})

        # Mock the setup dependencies
        mocker.patch.object(ACInfinityClient, "__init__", return_value=None)
        mocker.patch.object(ACInfinityClient, "close", new_callable=AsyncMock)
        mocker.patch.object(
            ConfigEntries, "async_forward_entry_setups", new_callable=AsyncMock
        )

        # Mock AC Infinity service with multiple new devices
        new_device_id_1 = "12345678901234567890"
        new_device_id_2 = "98765432109876543210"

        # Create test data for the new devices
        new_device_1_properties = {
            str(new_device_id_1): {
                ControllerPropertyKey.DEVICE_ID: new_device_id_1,
                ControllerPropertyKey.DEVICE_NAME: "Small Controller",
                ControllerPropertyKey.PORT_COUNT: 2,
                ControllerPropertyKey.DEVICE_INFO: {}
            }
        }

        new_device_2_properties = {
            str(new_device_id_2): {
                ControllerPropertyKey.DEVICE_ID: new_device_id_2,
                ControllerPropertyKey.DEVICE_NAME: "Large Controller",
                ControllerPropertyKey.PORT_COUNT: 6,
                ControllerPropertyKey.DEVICE_INFO: {}
            }
        }

        # Create a real ACInfinityService instance with mocked client
        mock_client = MagicMock()
        mock_ac_infinity = ACInfinityService(mock_client, ACInfinityData())
        mock_ac_infinity.refresh_controllers = AsyncMock()

        # Set up the service's cached data with new device data
        mock_ac_infinity.data.controller_properties = {
            **new_device_1_properties,
            **new_device_2_properties,
        }

        # Mock the get_device_ids method to return our new test device IDs
        mock_ac_infinity.get_device_ids = MagicMock(return_value=[new_device_id_1, new_device_id_2])

        mocker.patch("custom_components.ac_infinity.ACInfinityService", return_value=mock_ac_infinity)

        # Mock async_update_entry
        mock_update_entry = mocker.patch.object(hass.config_entries, "async_update_entry")

        # Execute setup
        result = await async_setup_entry(hass, config_entry)

        # Verify setup was successful
        assert result is True

        # Verify update was called
        mock_update_entry.assert_called()

        # Verify exactly one call was made and get its data
        mock_update_entry.assert_called_once()
        new_data = mock_update_entry.call_args[1]["data"]

        # Verify both devices were added
        assert str(new_device_id_1) in new_data[ConfigurationKey.ENTITIES]
        assert str(new_device_id_2) in new_data[ConfigurationKey.ENTITIES]

        # Verify first device (2 ports)
        device1_config = new_data[ConfigurationKey.ENTITIES][str(new_device_id_1)]
        assert device1_config["controller"] == EntityConfigValue.SENSORS_ONLY
        assert device1_config["sensors"] == EntityConfigValue.SENSORS_ONLY
        assert device1_config["port_1"] == EntityConfigValue.SENSORS_ONLY
        assert device1_config["port_2"] == EntityConfigValue.SENSORS_ONLY
        assert "port_3" not in device1_config  # Should not have port_3

        # Verify second device (6 ports)
        device2_config = new_data[ConfigurationKey.ENTITIES][str(new_device_id_2)]
        assert device2_config["controller"] == EntityConfigValue.SENSORS_ONLY
        assert device2_config["sensors"] == EntityConfigValue.SENSORS_ONLY
        assert device2_config["port_1"] == EntityConfigValue.SENSORS_ONLY
        assert device2_config["port_2"] == EntityConfigValue.SENSORS_ONLY
        assert device2_config["port_3"] == EntityConfigValue.SENSORS_ONLY
        assert device2_config["port_4"] == EntityConfigValue.SENSORS_ONLY
        assert device2_config["port_5"] == EntityConfigValue.SENSORS_ONLY
        assert device2_config["port_6"] == EntityConfigValue.SENSORS_ONLY

