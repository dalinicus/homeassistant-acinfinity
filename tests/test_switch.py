import asyncio
from asyncio import Future

import pytest
from pytest_mock import MockFixture

from custom_components.ac_infinity.const import DOMAIN, PortSettingKey
from custom_components.ac_infinity.switch import (
    SCHEDULE_DISABLED_VALUE,
    SCHEDULE_EOD_VALUE,
    SCHEDULE_MIDNIGHT_VALUE,
    ACInfinityPortSwitchEntity,
    async_setup_entry,
)
from tests import (
    ACTestObjects,
    execute_and_get_port_entity,
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

        assert len(test_objects.entities._added_entities) == 32

    @pytest.mark.parametrize(
        "setting",
        [
            PortSettingKey.AUTO_HUMIDITY_HIGH_ENABLED,
            PortSettingKey.AUTO_HUMIDITY_LOW_ENABLED,
            PortSettingKey.AUTO_TEMP_HIGH_ENABLED,
            PortSettingKey.AUTO_TEMP_LOW_ENABLED,
            PortSettingKey.VPD_HIGH_ENABLED,
            PortSettingKey.VPD_LOW_ENABLED,
            PortSettingKey.SCHEDULED_START_TIME,
            PortSettingKey.SCHEDULED_END_TIME,
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_mode_created_for_each_port(self, setup, port, setting):
        """Sensor for device port mode created on setup"""

        entity = await execute_and_get_port_entity(
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
            (PortSettingKey.AUTO_HUMIDITY_HIGH_ENABLED, 1, True),
            (PortSettingKey.AUTO_HUMIDITY_LOW_ENABLED, 1, True),
            (PortSettingKey.AUTO_TEMP_HIGH_ENABLED, 1, True),
            (PortSettingKey.AUTO_TEMP_LOW_ENABLED, 1, True),
            (PortSettingKey.VPD_HIGH_ENABLED, 1, True),
            (PortSettingKey.VPD_LOW_ENABLED, 1, True),
            (PortSettingKey.SCHEDULED_START_TIME, SCHEDULE_MIDNIGHT_VALUE, True),
            (PortSettingKey.SCHEDULED_END_TIME, SCHEDULE_MIDNIGHT_VALUE, True),
            # disabled
            (PortSettingKey.AUTO_HUMIDITY_HIGH_ENABLED, 0, False),
            (PortSettingKey.AUTO_HUMIDITY_LOW_ENABLED, 0, False),
            (PortSettingKey.AUTO_TEMP_HIGH_ENABLED, 0, False),
            (PortSettingKey.AUTO_TEMP_LOW_ENABLED, 0, False),
            (PortSettingKey.VPD_HIGH_ENABLED, 0, False),
            (PortSettingKey.VPD_LOW_ENABLED, 0, False),
            (PortSettingKey.SCHEDULED_START_TIME, SCHEDULE_DISABLED_VALUE, False),
            (PortSettingKey.SCHEDULED_END_TIME, SCHEDULE_DISABLED_VALUE, False),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_mode_value_correct(
        self, setup, setting, expected, port, value
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        test_objects.ac_infinity._port_settings[(str(DEVICE_ID), port)][setting] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortSwitchEntity)
        assert entity.is_on == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "setting,expected",
        [
            # enabled
            (PortSettingKey.AUTO_HUMIDITY_HIGH_ENABLED, 1),
            (PortSettingKey.AUTO_HUMIDITY_LOW_ENABLED, 1),
            (PortSettingKey.AUTO_TEMP_HIGH_ENABLED, 1),
            (PortSettingKey.AUTO_TEMP_LOW_ENABLED, 1),
            (PortSettingKey.VPD_HIGH_ENABLED, 1),
            (PortSettingKey.VPD_LOW_ENABLED, 1),
            (PortSettingKey.SCHEDULED_START_TIME, SCHEDULE_MIDNIGHT_VALUE),
            (PortSettingKey.SCHEDULED_END_TIME, SCHEDULE_EOD_VALUE),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_on(self, setup, expected, port, setting: str):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        assert isinstance(entity, ACInfinityPortSwitchEntity)
        await entity.async_turn_on()

        test_objects.port_set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "setting,expected",
        [
            (PortSettingKey.AUTO_HUMIDITY_HIGH_ENABLED, 0),
            (PortSettingKey.AUTO_HUMIDITY_LOW_ENABLED, 0),
            (PortSettingKey.AUTO_TEMP_HIGH_ENABLED, 0),
            (PortSettingKey.AUTO_TEMP_LOW_ENABLED, 0),
            (PortSettingKey.VPD_HIGH_ENABLED, 0),
            (PortSettingKey.VPD_LOW_ENABLED, 0),
            (PortSettingKey.SCHEDULED_START_TIME, SCHEDULE_DISABLED_VALUE),
            (PortSettingKey.SCHEDULED_END_TIME, SCHEDULE_DISABLED_VALUE),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_off(self, setup, expected, port, setting: str):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        assert isinstance(entity, ACInfinityPortSwitchEntity)
        await entity.async_turn_off()

        test_objects.port_set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
        test_objects.refresh_mock.assert_called()
