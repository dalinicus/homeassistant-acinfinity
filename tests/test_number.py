import asyncio
from asyncio import Future

import pytest
from homeassistant.components.number import NumberDeviceClass
from pytest_mock import MockFixture

from custom_components.ac_infinity.const import (
    DOMAIN,
    AdvancedSettingsKey,
    PortControlKey,
)
from custom_components.ac_infinity.number import (
    CONTROLLER_DESCRIPTIONS,
    PORT_DESCRIPTIONS,
    ACInfinityControllerNumberEntity,
    ACInfinityPortNumberEntity,
    async_setup_entry,
)
from tests import (
    ACTestObjects,
    execute_and_get_controller_entity,
    execute_and_get_port_entity,
    setup_entity_mocks,
)
from tests.data_models import DEVICE_ID, MAC_ADDR


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


@pytest.mark.asyncio
class TestNumbers:
    async def test_async_setup_all_sensors_created(self, setup):
        """All sensors created"""
        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 75

    @pytest.mark.parametrize(
        "setting", [PortControlKey.OFF_SPEED, PortControlKey.ON_SPEED]
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_entry_current_speed_created_for_each_port(
        self, setup, setting, port
    ):
        """Sensor for device port intensity created on setup"""

        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        assert isinstance(entity, ACInfinityPortNumberEntity)
        assert entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{setting}"
        assert entity.entity_description.device_class == NumberDeviceClass.POWER_FACTOR
        assert entity.entity_description.native_min_value == 0
        assert entity.entity_description.native_max_value == 10

        assert entity.device_info is not None

    @pytest.mark.parametrize(
        "setting,expected",
        [(PortControlKey.OFF_SPEED, 0), (PortControlKey.ON_SPEED, 5)],
    )
    async def test_async_update_current_speed_value_correct(
        self, setup, setting, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        test_objects: ACTestObjects = setup

        entity = await execute_and_get_port_entity(setup, async_setup_entry, 1, setting)
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortNumberEntity)
        assert entity.native_value == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "setting", [PortControlKey.OFF_SPEED, PortControlKey.ON_SPEED]
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value(self, setup, setting, port):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        assert isinstance(entity, ACInfinityPortNumberEntity)
        await entity.async_set_native_value(4)

        test_objects.port_control_set_mock.assert_called_with(str(DEVICE_ID), port, setting, 4)
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "key",
        [PortControlKey.TIMER_DURATION_TO_ON, PortControlKey.TIMER_DURATION_TO_OFF],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_timer_created_for_each_port(self, setup, key, port):
        """Setting for scheduled end time created on setup"""

        sensor = await execute_and_get_port_entity(setup, async_setup_entry, port, key)

        assert sensor.unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{key}"
        assert sensor.device_info is not None

    @pytest.mark.parametrize(
        "setting",
        [PortControlKey.TIMER_DURATION_TO_ON, PortControlKey.TIMER_DURATION_TO_OFF],
    )
    @pytest.mark.parametrize(
        "value,expected",
        [(86400, 1440), (1440, 24), (0, 0)],  # minutes to seconds
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_timer_value_correct(
        self,
        setup,
        setting,
        value,
        expected,
        port,
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        test_objects.ac_infinity._port_controls[(str(DEVICE_ID), port)][setting] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortNumberEntity)
        assert entity.native_value == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "expected,field_value",
        [(86400, 1440), (1440, 24), (0, 0)],  # minutes to seconds
    )
    @pytest.mark.parametrize(
        "setting",
        [PortControlKey.TIMER_DURATION_TO_ON, PortControlKey.TIMER_DURATION_TO_OFF],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_timer(
        self, setup, setting, expected: int, port, field_value
    ):
        """Reported entity value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup

        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        assert isinstance(entity, ACInfinityPortNumberEntity)
        await entity.async_set_native_value(field_value)

        test_objects.port_control_set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "key,label",
        [
            (PortControlKey.VPD_HIGH_TRIGGER, "High"),
            (PortControlKey.VPD_LOW_TRIGGER, "Low"),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_vpd_trigger_setup_for_each_port(
        self, setup, key, port, label
    ):
        """Setting for vpd trigger setup for each port"""

        entity = await execute_and_get_port_entity(setup, async_setup_entry, port, key)

        assert entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{key}"
        assert entity.device_info is not None

    @pytest.mark.parametrize(
        "setting,enabled_setting",
        [
            (PortControlKey.VPD_LOW_TRIGGER, PortControlKey.VPD_LOW_ENABLED),
            (PortControlKey.VPD_HIGH_TRIGGER, PortControlKey.VPD_HIGH_ENABLED),
        ],
    )
    @pytest.mark.parametrize(
        "value,expected",
        [(55, 5.5), (0, 0)],  # minutes to seconds
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_value_vpd(
        self, setup, setting, value, expected, port, enabled_setting
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        test_objects.ac_infinity._port_controls[(str(DEVICE_ID), port)][setting] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortNumberEntity)
        assert entity.native_value == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "setting",
        [
            PortControlKey.VPD_LOW_TRIGGER,
            PortControlKey.VPD_HIGH_TRIGGER,
        ],
    )
    @pytest.mark.parametrize(
        "expected,value,prev_value",
        [(55, 5.5, 45), (0, 0, 45)],  # minutes to seconds
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_vpd(
        self, setup, setting, value, expected, port, prev_value
    ):
        """Reported entity value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup

        test_objects.ac_infinity._port_controls[(str(DEVICE_ID), port)][
            setting
        ] = prev_value
        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        assert isinstance(entity, ACInfinityPortNumberEntity)
        await entity.async_set_native_value(value)

        test_objects.port_control_set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
        test_objects.refresh_mock.assert_called()

    #
    @pytest.mark.parametrize(
        "key", [PortControlKey.CYCLE_DURATION_ON, PortControlKey.CYCLE_DURATION_OFF]
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_cycle_timer_created_for_each_port(
        self, setup, key, port
    ):
        """Setting for scheduled end time created on setup"""

        entity = await execute_and_get_port_entity(setup, async_setup_entry, port, key)

        assert entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{key}"
        assert entity.device_info is not None

    @pytest.mark.parametrize(
        "setting", [PortControlKey.CYCLE_DURATION_ON, PortControlKey.CYCLE_DURATION_OFF]
    )
    @pytest.mark.parametrize(
        "value,expected",
        [(86400, 1440), (1440, 24), (0, 0)],  # minutes to seconds
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_cycle_timer_value_correct(
        self,
        setup,
        setting,
        value,
        expected,
        port,
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        test_objects.ac_infinity._port_controls[(str(DEVICE_ID), port)][setting] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortNumberEntity)
        assert entity.native_value == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "expected,field_value",
        [(86400, 1440), (1440, 24), (0, 0)],  # minutes to seconds
    )
    @pytest.mark.parametrize(
        "setting", [PortControlKey.CYCLE_DURATION_ON, PortControlKey.CYCLE_DURATION_OFF]
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_cycle_timer(
        self, setup, setting, expected: int, port, field_value
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup

        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        assert isinstance(entity, ACInfinityPortNumberEntity)
        await entity.async_set_native_value(field_value)

        test_objects.port_control_set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "setting, f_setting",
        [
            (
                PortControlKey.AUTO_TEMP_HIGH_TRIGGER,
                PortControlKey.AUTO_TEMP_HIGH_TRIGGER_F,
            ),
            (
                PortControlKey.AUTO_TEMP_LOW_TRIGGER,
                PortControlKey.AUTO_TEMP_LOW_TRIGGER_F,
            ),
        ],
    )
    @pytest.mark.parametrize(
        "c,f",
        [(0, 32), (90, 194), (46, 115)],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_temp_trigger_correct(
        self,
        setup,
        setting,
        f_setting,
        c,
        f,
        port,
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        test_objects.ac_infinity._port_controls[(str(DEVICE_ID), port)][setting] = c
        test_objects.ac_infinity._port_controls[(str(DEVICE_ID), port)][f_setting] = f
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortNumberEntity)
        assert entity.native_value == c
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "c,f",
        [(0, 32), (90, 194), (46, 115)],
    )
    @pytest.mark.parametrize(
        "setting, f_setting",
        [
            (
                PortControlKey.AUTO_TEMP_HIGH_TRIGGER,
                PortControlKey.AUTO_TEMP_HIGH_TRIGGER_F,
            ),
            (
                PortControlKey.AUTO_TEMP_LOW_TRIGGER,
                PortControlKey.AUTO_TEMP_LOW_TRIGGER_F,
            ),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_temp_trigger_value(
        self, setup, setting, c, f, port, f_setting
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup

        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        assert isinstance(entity, ACInfinityPortNumberEntity)
        await entity.async_set_native_value(c)

        test_objects.port_control_sets_mock.assert_called_with(
            str(DEVICE_ID), port, [(setting, c), (f_setting, f)]
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "setting",
        [
            AdvancedSettingsKey.CALIBRATE_TEMP,
            AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET,
        ],
    )
    @pytest.mark.parametrize("temp_unit,expected", [(0, 20), (1, 10)])
    async def test_async_setup_entry_temp_calibration_created(
        self, setup, setting, temp_unit, expected
    ):
        """Sensor for device reported temperature is created on setup"""
        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._device_settings[(str(DEVICE_ID), 1)][
            AdvancedSettingsKey.TEMP_UNIT
        ] = temp_unit

        # reset statistics
        for description in CONTROLLER_DESCRIPTIONS:
            if description.key != AdvancedSettingsKey.CALIBRATE_HUMIDITY:
                description.native_min_value = -20
                description.native_max_value = 20

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, setting
        )

        assert entity.device_info is not None

        assert isinstance(entity, ACInfinityControllerNumberEntity)
        assert entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_{setting}"
        assert entity.entity_description.device_class is None
        assert entity.entity_description.native_min_value == expected * -1
        assert entity.entity_description.native_max_value == expected

        assert entity.device_info is not None

    async def test_async_setup_entry_humidity_calibration_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, AdvancedSettingsKey.CALIBRATE_HUMIDITY
        )

        assert entity.device_info is not None

        assert isinstance(entity, ACInfinityControllerNumberEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{MAC_ADDR}_{AdvancedSettingsKey.CALIBRATE_HUMIDITY}"
        )
        assert entity.entity_description.device_class is None
        assert entity.entity_description.native_min_value == -10
        assert entity.entity_description.native_max_value == 10

        assert entity.device_info is not None

    @pytest.mark.parametrize(
        "setting",
        [
            AdvancedSettingsKey.CALIBRATE_TEMP,
            AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET,
            AdvancedSettingsKey.CALIBRATE_HUMIDITY,
        ],
    )
    @pytest.mark.parametrize("value", [-10, 0, 5])
    async def test_async_update_calibration(self, setup, setting, value):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, setting
        )

        test_objects.ac_infinity._device_settings[(str(DEVICE_ID), 0)][setting] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityControllerNumberEntity)
        assert entity.native_value == value
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "temp_unit,value,expected",
        [
            # F max is ±20
            (0, -20, -20),
            (0, 0, 0),
            (0, 20, 20),
            # C max is -10
            (1, -20, -10),
            (1, 0, 0),
            (1, 20, 10),
        ],
    )
    async def test_async_set_native_value_temp_calibration(
        self, setup, temp_unit, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._device_settings[(str(DEVICE_ID), 0)][
            AdvancedSettingsKey.TEMP_UNIT
        ] = temp_unit

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, AdvancedSettingsKey.CALIBRATE_TEMP
        )

        assert isinstance(entity, ACInfinityControllerNumberEntity)
        await entity.async_set_native_value(value)

        if temp_unit > 0:
            test_objects.controller_sets_mock.assert_called_with(
                str(DEVICE_ID),
                [
                    (AdvancedSettingsKey.CALIBRATE_TEMP, expected),
                    (AdvancedSettingsKey.CALIBRATE_TEMP_F, 0),
                ],
            )
        else:
            test_objects.controller_sets_mock.assert_called_with(
                str(DEVICE_ID),
                [
                    (AdvancedSettingsKey.CALIBRATE_TEMP, 0),
                    (AdvancedSettingsKey.CALIBRATE_TEMP_F, expected),
                ],
            )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "temp_unit,value,expected",
        [
            # F max is ±20
            (0, -20, -20),
            (0, 0, 0),
            (0, 20, 20),
            # C max is -10
            (1, -20, -10),
            (1, 0, 0),
            (1, 20, 10),
        ],
    )
    async def test_async_set_native_value_vpd_leaf_temp_calibration(
        self, setup, temp_unit, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._device_settings[(str(DEVICE_ID), 0)][
            AdvancedSettingsKey.TEMP_UNIT
        ] = temp_unit

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET
        )

        assert isinstance(entity, ACInfinityControllerNumberEntity)
        await entity.async_set_native_value(value)

        test_objects.controller_set_mock.assert_called_with(
            str(DEVICE_ID),
            AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET
            if temp_unit > 0
            else AdvancedSettingsKey.VPD_LEAF_TEMP_OFFSET_F,
            expected,
        )

        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("value", [10, -10, 0])
    async def test_async_set_native_value_humidity_calibration(
        self,
        setup,
        value,
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, AdvancedSettingsKey.CALIBRATE_HUMIDITY
        )

        assert isinstance(entity, ACInfinityControllerNumberEntity)
        await entity.async_set_native_value(value)

        test_objects.controller_set_mock.assert_called_with(
            str(DEVICE_ID), AdvancedSettingsKey.CALIBRATE_HUMIDITY, value
        )

        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "setting",
        [AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP, AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP],
    )
    @pytest.mark.parametrize("temp_unit,expected", [(0, 20), (1, 10)])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_dynamic_temp_setup_for_each_port(
        self, setup, setting: str, port, temp_unit, expected
    ):
        """Dynamic response temp controls setup for each port"""
        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._device_settings[(str(DEVICE_ID), port)][
            AdvancedSettingsKey.TEMP_UNIT
        ] = temp_unit

        # reset statistics
        for description in PORT_DESCRIPTIONS:
            if description.key == setting:
                description.native_max_value = 20

        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        assert entity.device_info is not None

        assert isinstance(entity, ACInfinityPortNumberEntity)
        assert entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{setting}"
        assert entity.entity_description.device_class is None
        assert entity.entity_description.native_min_value == 0
        assert entity.entity_description.native_max_value == expected

        assert entity.device_info is not None

    @pytest.mark.parametrize(
        "setting,step,max_value",
        [
            (AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY, 1, 10),
            (AdvancedSettingsKey.DYNAMIC_BUFFER_HUMIDITY, 1, 10),
            (AdvancedSettingsKey.DYNAMIC_TRANSITION_VPD, 0.1, 1),
            (AdvancedSettingsKey.DYNAMIC_BUFFER_VPD, 0.1, 1),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_dynamic_humidity_vpd_setup_for_each_port(
        self, setup, port, setting: str, step, max_value
    ):
        """Dynamic response temp controls setup for each port"""
        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        assert entity.device_info is not None

        assert isinstance(entity, ACInfinityPortNumberEntity)
        assert entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{setting}"
        assert entity.entity_description.device_class is None
        assert entity.entity_description.native_step == step
        assert entity.entity_description.native_min_value == 0
        assert entity.entity_description.native_max_value == max_value

        assert entity.device_info is not None

    @pytest.mark.parametrize(
        "setting,value,expected",
        [
            (AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP, 8, 8),
            (AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY, 8, 8),
            (AdvancedSettingsKey.DYNAMIC_TRANSITION_VPD, 8, 0.8),
            (AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP, 8, 8),
            (AdvancedSettingsKey.DYNAMIC_BUFFER_HUMIDITY, 8, 8),
            (AdvancedSettingsKey.DYNAMIC_BUFFER_VPD, 8, 0.8),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_dynamic_response(
        self, setup, setting: str, value, expected, port
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        test_objects.ac_infinity._device_settings[(str(DEVICE_ID), port)][setting] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortNumberEntity)
        assert entity.native_value == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "setting,f_setting",
        [
            (
                AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP,
                AdvancedSettingsKey.DYNAMIC_TRANSITION_TEMP_F,
            ),
            (AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP, AdvancedSettingsKey.DYNAMIC_BUFFER_TEMP_F),
        ],
    )
    @pytest.mark.parametrize(
        "temp_unit,value,f_expected,expected",
        [
            # F max is 20
            (0, 0, 0, 0),
            (0, 10, 10, 5),
            (0, 11, 11, 5),
            (0, 20, 20, 10),
            # C max is 10
            (1, 0, 0, 0),
            (1, 5, 10, 5),
            (1, 6, 12, 6),
            (1, 10, 20, 10),
            (1, 20, 20, 10),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_dynamic_response_temp(
        self, setup, temp_unit, value, expected, f_expected, setting, f_setting, port
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._device_settings[(str(DEVICE_ID), port)][
            AdvancedSettingsKey.TEMP_UNIT
        ] = temp_unit

        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        assert isinstance(entity, ACInfinityPortNumberEntity)
        await entity.async_set_native_value(value)

        if temp_unit > 0:
            test_objects.port_setting_sets_mock.assert_called_with(
                str(DEVICE_ID),
                port,
                [
                    (setting, expected),
                    (f_setting, f_expected),
                ],
            )
        else:
            test_objects.port_setting_sets_mock.assert_called_with(
                str(DEVICE_ID),
                port,
                [
                    (setting, expected),
                    (f_setting, f_expected),
                ],
            )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "setting",
        [
            AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY,
            AdvancedSettingsKey.DYNAMIC_BUFFER_HUMIDITY,
        ],
    )
    @pytest.mark.parametrize("value", [0, 5, 10])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_dynamic_response_humidity(
        self, setup, value, port, setting
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup

        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        assert isinstance(entity, ACInfinityPortNumberEntity)
        await entity.async_set_native_value(value)

        test_objects.port_setting_set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, value
        )

        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "setting",
        [AdvancedSettingsKey.DYNAMIC_TRANSITION_VPD, AdvancedSettingsKey.DYNAMIC_BUFFER_VPD],
    )
    @pytest.mark.parametrize("expected,value", [(0, 0), (5, 0.5), (10, 1)])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_dynamic_response_vpd(
        self, setup, value, expected, port, setting
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup

        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        assert isinstance(entity, ACInfinityPortNumberEntity)
        await entity.async_set_native_value(value)

        test_objects.port_setting_set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )

        test_objects.refresh_mock.assert_called()
