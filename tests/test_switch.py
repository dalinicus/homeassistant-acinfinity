import asyncio
from asyncio import Future

import pytest
from pytest_mock import MockFixture

from custom_components.ac_infinity.const import (
    DOMAIN,
    AdvancedSettingsKey,
    DeviceControlKey,
)
from custom_components.ac_infinity.switch import (
    SCHEDULE_DISABLED_VALUE,
    SCHEDULE_EOD_VALUE,
    SCHEDULE_MIDNIGHT_VALUE,
    ACInfinityDeviceSwitchEntity,
    async_setup_entry,
)
from tests import (
    ACTestObjects,
    execute_and_get_device_entity,
    setup_entity_mocks,
)
from tests.data_models import DEVICE_ID, MAC_ADDR


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


@pytest.mark.asyncio
class TestSwitches:
    async def test_async_setup_all_sensors_created(self, setup):
        """All sensors created"""
        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 48

    @pytest.mark.parametrize(
        "setting",
        [
            DeviceControlKey.AUTO_HUMIDITY_HIGH_ENABLED,
            DeviceControlKey.AUTO_HUMIDITY_LOW_ENABLED,
            DeviceControlKey.AUTO_TEMP_HIGH_ENABLED,
            DeviceControlKey.AUTO_TEMP_LOW_ENABLED,
            DeviceControlKey.VPD_HIGH_ENABLED,
            DeviceControlKey.VPD_LOW_ENABLED,
            DeviceControlKey.SCHEDULED_START_TIME,
            DeviceControlKey.SCHEDULED_END_TIME,
            AdvancedSettingsKey.SUNRISE_TIMER_ENABLED,
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_mode_created_for_each_port(self, setup, port, setting):
        """Sensor for device port mode created on setup"""

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        assert entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{setting}"
        assert entity.device_info is not None

    @pytest.mark.parametrize(
        "setting,value,expected",
        [
            # enabled
            (DeviceControlKey.AUTO_HUMIDITY_HIGH_ENABLED, 1, True),
            (DeviceControlKey.AUTO_HUMIDITY_LOW_ENABLED, 1, True),
            (DeviceControlKey.AUTO_TEMP_HIGH_ENABLED, 1, True),
            (DeviceControlKey.AUTO_TEMP_LOW_ENABLED, 1, True),
            (DeviceControlKey.VPD_HIGH_ENABLED, 1, True),
            (DeviceControlKey.VPD_LOW_ENABLED, 1, True),
            (DeviceControlKey.SCHEDULED_START_TIME, SCHEDULE_MIDNIGHT_VALUE, True),
            (DeviceControlKey.SCHEDULED_END_TIME, SCHEDULE_MIDNIGHT_VALUE, True),
            # disabled
            (DeviceControlKey.AUTO_HUMIDITY_HIGH_ENABLED, 0, False),
            (DeviceControlKey.AUTO_HUMIDITY_LOW_ENABLED, 0, False),
            (DeviceControlKey.AUTO_TEMP_HIGH_ENABLED, 0, False),
            (DeviceControlKey.AUTO_TEMP_LOW_ENABLED, 0, False),
            (DeviceControlKey.VPD_HIGH_ENABLED, 0, False),
            (DeviceControlKey.VPD_LOW_ENABLED, 0, False),
            (DeviceControlKey.SCHEDULED_START_TIME, SCHEDULE_DISABLED_VALUE, False),
            (DeviceControlKey.SCHEDULED_END_TIME, SCHEDULE_DISABLED_VALUE, False),
            # None
            (DeviceControlKey.AUTO_HUMIDITY_HIGH_ENABLED, None, False),
            (DeviceControlKey.AUTO_HUMIDITY_LOW_ENABLED, None, False),
            (DeviceControlKey.AUTO_TEMP_HIGH_ENABLED, None, False),
            (DeviceControlKey.AUTO_TEMP_LOW_ENABLED, None, False),
            (DeviceControlKey.VPD_HIGH_ENABLED, None, False),
            (DeviceControlKey.VPD_LOW_ENABLED, None, False),
            (DeviceControlKey.SCHEDULED_START_TIME, None, False),
            (DeviceControlKey.SCHEDULED_END_TIME, None, False),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_port_control_value_correct(
        self, setup, setting, expected, port, value
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        test_objects.ac_infinity._device_controls[(str(DEVICE_ID), port)][setting] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        assert entity.is_on == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "setting,value,expected",
        [
            # enabled
            (AdvancedSettingsKey.SUNRISE_TIMER_ENABLED, 1, True),
            # disabled
            (AdvancedSettingsKey.SUNRISE_TIMER_ENABLED, 0, False),
            # None
            (AdvancedSettingsKey.SUNRISE_TIMER_ENABLED, None, False),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_port_setting_value_correct(
        self, setup, setting, value, expected, port
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, setting
        )

        test_objects.ac_infinity._device_settings[(str(DEVICE_ID), port)][
            setting
        ] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        assert entity.is_on == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "setting,expected",
        [
            # enabled
            (DeviceControlKey.AUTO_HUMIDITY_HIGH_ENABLED, 1),
            (DeviceControlKey.AUTO_HUMIDITY_LOW_ENABLED, 1),
            (DeviceControlKey.AUTO_TEMP_HIGH_ENABLED, 1),
            (DeviceControlKey.AUTO_TEMP_LOW_ENABLED, 1),
            (DeviceControlKey.VPD_HIGH_ENABLED, 1),
            (DeviceControlKey.VPD_LOW_ENABLED, 1),
            (DeviceControlKey.SCHEDULED_START_TIME, SCHEDULE_MIDNIGHT_VALUE),
            (DeviceControlKey.SCHEDULED_END_TIME, SCHEDULE_EOD_VALUE),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_on_port_control(
        self, setup, expected, port, setting: str
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_on()

        test_objects.port_control_set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "setting,expected",
        [
            # enabled
            (AdvancedSettingsKey.SUNRISE_TIMER_ENABLED, 1)
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_on_port_setting(
        self, setup, expected, port, setting: str
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_on()

        test_objects.port_setting_set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "setting,expected",
        [
            (DeviceControlKey.AUTO_HUMIDITY_HIGH_ENABLED, 0),
            (DeviceControlKey.AUTO_HUMIDITY_LOW_ENABLED, 0),
            (DeviceControlKey.AUTO_TEMP_HIGH_ENABLED, 0),
            (DeviceControlKey.AUTO_TEMP_LOW_ENABLED, 0),
            (DeviceControlKey.VPD_HIGH_ENABLED, 0),
            (DeviceControlKey.VPD_LOW_ENABLED, 0),
            (DeviceControlKey.SCHEDULED_START_TIME, SCHEDULE_DISABLED_VALUE),
            (DeviceControlKey.SCHEDULED_END_TIME, SCHEDULE_DISABLED_VALUE),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_off_port_control(
        self, setup, expected, port, setting: str
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_off()

        test_objects.port_control_set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "setting,expected",
        [(AdvancedSettingsKey.SUNRISE_TIMER_ENABLED, 0)],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_off_port_setting(
        self, setup, expected, port, setting: str
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_off()

        test_objects.port_setting_set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
        test_objects.refresh_mock.assert_called()
