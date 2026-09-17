import asyncio
from asyncio import Future
from copy import deepcopy

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
from tests.data_models import AI_DEVICE_ID, AI_MAC_ADDR


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

        assert len(test_objects.entities._added_entities) == 52

    @pytest.mark.parametrize(
        "setting",
        [
            DeviceControlKey.AUTO_HUMIDITY_HIGH_ENABLED,
            DeviceControlKey.AUTO_HUMIDITY_LOW_ENABLED,
            DeviceControlKey.AUTO_TEMP_HIGH_ENABLED,
            DeviceControlKey.AUTO_TEMP_LOW_ENABLED,
            DeviceControlKey.TARGET_TEMP_SWITCH,
            DeviceControlKey.TARGET_HUMI_SWITCH,
            DeviceControlKey.VPD_HIGH_ENABLED,
            DeviceControlKey.VPD_LOW_ENABLED,
            DeviceControlKey.TARGET_VPD_SWITCH,
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

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_co2_low_switch_created_for_ai_port(self, setup, port):
        """CO2 low switch entity is created only for AI devices in CO2 mode."""
        test_objects: ACTestObjects = setup

        # Seed AI controls so suitability and mode checks can resolve for AI ports.
        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 2
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), port)][DeviceControlKey.AT_TYPE] = 9

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.CO2_LOW_SWITCH,
            AI_MAC_ADDR,
        )

        assert entity.unique_id == f"{DOMAIN}_{AI_MAC_ADDR}_port_{port}_{DeviceControlKey.CO2_LOW_SWITCH}"
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(1, True), (0, False), (None, False)])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_ai_port_co2_low_switch_value_correct(self, setup, port, value, expected):
        """CO2 low switch value is read from AI control payload."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 9
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.CO2_LOW_SWITCH,
            AI_MAC_ADDR,
        )

        test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), port)][
            DeviceControlKey.CO2_LOW_SWITCH
        ] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        assert entity.is_on == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize("expected", [1])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_on_ai_port_co2_low_switch(self, setup, port, expected):
        """CO2 low switch turn on updates AI control."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 9
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.CO2_LOW_SWITCH,
            AI_MAC_ADDR,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_on()

        test_objects.port_control_set_mock.assert_called_with(
            entity._device, DeviceControlKey.CO2_LOW_SWITCH, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("expected", [0])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_off_ai_port_co2_low_switch(self, setup, port, expected):
        """CO2 low switch turn off updates AI control."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 9
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.CO2_LOW_SWITCH,
            AI_MAC_ADDR,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_off()

        test_objects.port_control_set_mock.assert_called_with(
            entity._device, DeviceControlKey.CO2_LOW_SWITCH, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_co2_fan_high_switch_created_for_ai_port(self, setup, port):
        """CO2 fan high switch entity is created only for AI devices in CO2 Fan mode."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 2
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), port)][DeviceControlKey.AT_TYPE] = 10

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.CO2_FAN_HIGH_SWITCH,
            AI_MAC_ADDR,
        )

        assert entity.unique_id == f"{DOMAIN}_{AI_MAC_ADDR}_port_{port}_{DeviceControlKey.CO2_FAN_HIGH_SWITCH}"
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(1, True), (0, False), (None, False)])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_ai_port_co2_fan_high_switch_value_correct(self, setup, port, value, expected):
        """CO2 fan high switch value is read from AI control payload."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 10
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.CO2_FAN_HIGH_SWITCH,
            AI_MAC_ADDR,
        )

        test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), port)][
            DeviceControlKey.CO2_FAN_HIGH_SWITCH
        ] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        assert entity.is_on == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize("expected", [1])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_on_ai_port_co2_fan_high_switch(self, setup, port, expected):
        """CO2 fan high switch turn on updates AI control."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 10
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.CO2_FAN_HIGH_SWITCH,
            AI_MAC_ADDR,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_on()

        test_objects.port_control_set_mock.assert_called_with(
            entity._device, DeviceControlKey.CO2_FAN_HIGH_SWITCH, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("expected", [0])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_off_ai_port_co2_fan_high_switch(self, setup, port, expected):
        """CO2 fan high switch turn off updates AI control."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 10
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.CO2_FAN_HIGH_SWITCH,
            AI_MAC_ADDR,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_off()

        test_objects.port_control_set_mock.assert_called_with(
            entity._device, DeviceControlKey.CO2_FAN_HIGH_SWITCH, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_moisture_low_switch_created_for_ai_port(self, setup, port):
        """Moisture low switch entity is created only for AI devices in moisture mode."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 2
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), port)][DeviceControlKey.AT_TYPE] = 11

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.MOISTURE_LOW_SWITCH,
            AI_MAC_ADDR,
        )

        assert entity.unique_id == f"{DOMAIN}_{AI_MAC_ADDR}_port_{port}_{DeviceControlKey.MOISTURE_LOW_SWITCH}"
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(1, True), (0, False), (None, False)])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_ai_port_moisture_low_switch_value_correct(self, setup, port, value, expected):
        """Moisture low switch value is read from AI control payload."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 11
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.MOISTURE_LOW_SWITCH,
            AI_MAC_ADDR,
        )

        test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), port)][
            DeviceControlKey.MOISTURE_LOW_SWITCH
        ] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        assert entity.is_on == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize("expected", [1])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_on_ai_port_moisture_low_switch(self, setup, port, expected):
        """Moisture low switch turn on updates AI control."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 11
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.MOISTURE_LOW_SWITCH,
            AI_MAC_ADDR,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_on()

        test_objects.port_control_set_mock.assert_called_with(
            entity._device, DeviceControlKey.MOISTURE_LOW_SWITCH, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("expected", [0])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_off_ai_port_moisture_low_switch(self, setup, port, expected):
        """Moisture low switch turn off updates AI control."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 11
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.MOISTURE_LOW_SWITCH,
            AI_MAC_ADDR,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_off()

        test_objects.port_control_set_mock.assert_called_with(
            entity._device, DeviceControlKey.MOISTURE_LOW_SWITCH, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_ec_tds_low_switch_ec_created_for_ai_port(self, setup, port):
        """EC low switch entity is created only for AI devices in EC mode."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 2
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), port)][DeviceControlKey.AT_TYPE] = 14

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.EC_TDS_LOW_SWITCH_EC,
            AI_MAC_ADDR,
        )

        assert entity.unique_id == f"{DOMAIN}_{AI_MAC_ADDR}_port_{port}_{DeviceControlKey.EC_TDS_LOW_SWITCH_EC}"
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(1, True), (0, False), (None, False)])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_ai_port_ec_tds_low_switch_ec_value_correct(self, setup, port, value, expected):
        """EC low switch value is read from AI control payload."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 14
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.EC_TDS_LOW_SWITCH_EC,
            AI_MAC_ADDR,
        )

        test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), port)][
            DeviceControlKey.EC_TDS_LOW_SWITCH_EC
        ] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        assert entity.is_on == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize("expected", [1])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_on_ai_port_ec_tds_low_switch_ec(self, setup, port, expected):
        """EC low switch turn on updates AI control."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 14
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.EC_TDS_LOW_SWITCH_EC,
            AI_MAC_ADDR,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_on()

        test_objects.port_control_set_mock.assert_called_with(
            entity._device, DeviceControlKey.EC_TDS_LOW_SWITCH_EC, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("expected", [0])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_off_ai_port_ec_tds_low_switch_ec(self, setup, port, expected):
        """EC low switch turn off updates AI control."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 14
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.EC_TDS_LOW_SWITCH_EC,
            AI_MAC_ADDR,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_off()

        test_objects.port_control_set_mock.assert_called_with(
            entity._device, DeviceControlKey.EC_TDS_LOW_SWITCH_EC, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("setting", [DeviceControlKey.PH_HIGH_SWITCH, DeviceControlKey.PH_LOW_SWITCH])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_ph_switch_created_for_ai_port(self, setup, setting, port):
        """pH switch entities are created only for AI devices in pH mode."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 2
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), port)][DeviceControlKey.AT_TYPE] = 13

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
            AI_MAC_ADDR,
        )

        assert entity.unique_id == f"{DOMAIN}_{AI_MAC_ADDR}_port_{port}_{setting}"
        assert entity.device_info is not None

    @pytest.mark.parametrize("setting", [DeviceControlKey.PH_HIGH_SWITCH, DeviceControlKey.PH_LOW_SWITCH])
    @pytest.mark.parametrize("value,expected", [(1, True), (0, False), (None, False)])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_ai_port_ph_switch_value_correct(self, setup, setting, port, value, expected):
        """pH switch values are read from AI control payload."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 13
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
            AI_MAC_ADDR,
        )

        test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), port)][setting] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        assert entity.is_on == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize("setting", [DeviceControlKey.PH_HIGH_SWITCH, DeviceControlKey.PH_LOW_SWITCH])
    @pytest.mark.parametrize("expected", [1])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_on_ai_port_ph_switch(self, setup, setting, port, expected):
        """pH switch turn on updates AI control."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 13
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
            AI_MAC_ADDR,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_on()

        test_objects.port_control_set_mock.assert_called_with(
            entity._device, setting, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("setting", [DeviceControlKey.PH_HIGH_SWITCH, DeviceControlKey.PH_LOW_SWITCH])
    @pytest.mark.parametrize("expected", [0])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_off_ai_port_ph_switch(self, setup, setting, port, expected):
        """pH switch turn off updates AI control."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 13
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
            AI_MAC_ADDR,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_off()

        test_objects.port_control_set_mock.assert_called_with(
            entity._device, setting, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("setting", [DeviceControlKey.WATER_TEMP_HIGH_SWITCH, DeviceControlKey.WATER_TEMP_LOW_SWITCH])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_water_temp_switch_created_for_ai_port(self, setup, setting, port):
        """Water temp switches are created only for AI devices in water temp mode."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 2
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), port)][DeviceControlKey.AT_TYPE] = 12

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
            AI_MAC_ADDR,
        )

        assert entity.unique_id == f"{DOMAIN}_{AI_MAC_ADDR}_port_{port}_{setting}"
        assert entity.device_info is not None

    @pytest.mark.parametrize("setting", [DeviceControlKey.WATER_TEMP_HIGH_SWITCH, DeviceControlKey.WATER_TEMP_LOW_SWITCH])
    @pytest.mark.parametrize("value,expected", [(1, True), (0, False), (None, False)])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_ai_port_water_temp_switch_value_correct(self, setup, setting, port, value, expected):
        """Water temp switch values are read from AI control payload."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 12
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
            AI_MAC_ADDR,
        )

        test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), port)][setting] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        assert entity.is_on == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize("setting", [DeviceControlKey.WATER_TEMP_HIGH_SWITCH, DeviceControlKey.WATER_TEMP_LOW_SWITCH])
    @pytest.mark.parametrize("expected", [1])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_on_ai_port_water_temp_switch(self, setup, setting, port, expected):
        """Water temp switch turn on updates AI control."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 12
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
            AI_MAC_ADDR,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_on()

        test_objects.port_control_set_mock.assert_called_with(entity._device, setting, expected)
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("setting", [DeviceControlKey.WATER_TEMP_HIGH_SWITCH, DeviceControlKey.WATER_TEMP_LOW_SWITCH])
    @pytest.mark.parametrize("expected", [0])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_off_ai_port_water_temp_switch(self, setup, setting, port, expected):
        """Water temp switch turn off updates AI control."""
        test_objects: ACTestObjects = setup

        for ai_port in [1, 2, 3, 4]:
            ai_control = deepcopy(test_objects.ac_infinity._device_controls[(str(DEVICE_ID), 1)])
            ai_control[DeviceControlKey.AT_TYPE] = 12
            test_objects.ac_infinity._device_controls[(str(AI_DEVICE_ID), ai_port)] = ai_control

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
            AI_MAC_ADDR,
        )

        assert isinstance(entity, ACInfinityDeviceSwitchEntity)
        await entity.async_turn_off()

        test_objects.port_control_set_mock.assert_called_with(entity._device, setting, expected)
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "setting,value,expected",
        [
            # enabled
            (DeviceControlKey.AUTO_HUMIDITY_HIGH_ENABLED, 1, True),
            (DeviceControlKey.AUTO_HUMIDITY_LOW_ENABLED, 1, True),
            (DeviceControlKey.AUTO_TEMP_HIGH_ENABLED, 1, True),
            (DeviceControlKey.AUTO_TEMP_LOW_ENABLED, 1, True),
            (DeviceControlKey.TARGET_TEMP_SWITCH, 1, True),
            (DeviceControlKey.TARGET_HUMI_SWITCH, 1, True),
            (DeviceControlKey.VPD_HIGH_ENABLED, 1, True),
            (DeviceControlKey.VPD_LOW_ENABLED, 1, True),
            (DeviceControlKey.TARGET_VPD_SWITCH, 1, True),
            (DeviceControlKey.SCHEDULED_START_TIME, SCHEDULE_MIDNIGHT_VALUE, True),
            (DeviceControlKey.SCHEDULED_END_TIME, SCHEDULE_MIDNIGHT_VALUE, True),
            # disabled
            (DeviceControlKey.AUTO_HUMIDITY_HIGH_ENABLED, 0, False),
            (DeviceControlKey.AUTO_HUMIDITY_LOW_ENABLED, 0, False),
            (DeviceControlKey.AUTO_TEMP_HIGH_ENABLED, 0, False),
            (DeviceControlKey.AUTO_TEMP_LOW_ENABLED, 0, False),
            (DeviceControlKey.TARGET_TEMP_SWITCH, 0, False),
            (DeviceControlKey.TARGET_HUMI_SWITCH, 0, False),
            (DeviceControlKey.VPD_HIGH_ENABLED, 0, False),
            (DeviceControlKey.VPD_LOW_ENABLED, 0, False),
            (DeviceControlKey.TARGET_VPD_SWITCH, 0, False),
            (DeviceControlKey.SCHEDULED_START_TIME, SCHEDULE_DISABLED_VALUE, False),
            (DeviceControlKey.SCHEDULED_END_TIME, SCHEDULE_DISABLED_VALUE, False),
            # None
            (DeviceControlKey.AUTO_HUMIDITY_HIGH_ENABLED, None, False),
            (DeviceControlKey.AUTO_HUMIDITY_LOW_ENABLED, None, False),
            (DeviceControlKey.AUTO_TEMP_HIGH_ENABLED, None, False),
            (DeviceControlKey.AUTO_TEMP_LOW_ENABLED, None, False),
            (DeviceControlKey.TARGET_TEMP_SWITCH, None, False),
            (DeviceControlKey.TARGET_HUMI_SWITCH, None, False),
            (DeviceControlKey.VPD_HIGH_ENABLED, None, False),
            (DeviceControlKey.VPD_LOW_ENABLED, None, False),
            (DeviceControlKey.TARGET_VPD_SWITCH, None, False),
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
            (DeviceControlKey.TARGET_TEMP_SWITCH, 1),
            (DeviceControlKey.TARGET_HUMI_SWITCH, 1),
            (DeviceControlKey.VPD_HIGH_ENABLED, 1),
            (DeviceControlKey.VPD_LOW_ENABLED, 1),
            (DeviceControlKey.TARGET_VPD_SWITCH, 1),
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
            entity._device, setting, expected
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
            entity._device, setting, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "setting,expected",
        [
            (DeviceControlKey.AUTO_HUMIDITY_HIGH_ENABLED, 0),
            (DeviceControlKey.AUTO_HUMIDITY_LOW_ENABLED, 0),
            (DeviceControlKey.AUTO_TEMP_HIGH_ENABLED, 0),
            (DeviceControlKey.AUTO_TEMP_LOW_ENABLED, 0),
            (DeviceControlKey.TARGET_TEMP_SWITCH, 0),
            (DeviceControlKey.TARGET_HUMI_SWITCH, 0),
            (DeviceControlKey.VPD_HIGH_ENABLED, 0),
            (DeviceControlKey.VPD_LOW_ENABLED, 0),
            (DeviceControlKey.TARGET_VPD_SWITCH, 0),
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
            entity._device, setting, expected
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
            entity._device, setting, expected
        )
        test_objects.refresh_mock.assert_called()
