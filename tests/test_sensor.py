from datetime import datetime

import pytest
from freezegun import freeze_time
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
)
from pytest_mock import MockFixture
from zoneinfo import ZoneInfo

from custom_components.ac_infinity.const import (
    DOMAIN,
    ControllerPropertyKey,
    CustomPortPropertyKey,
    PortPropertyKey,
    SensorKeys,
)
from custom_components.ac_infinity.sensor import (
    ACInfinityControllerSensorEntity,
    ACInfinityPortSensorEntity,
    ACInfinitySensorSensorEntity,
    async_setup_entry,
)
from tests import (
    ACTestObjects,
    execute_and_get_controller_entity,
    execute_and_get_device_entity,
    execute_and_get_sensor_entity,
    setup_entity_mocks,
)
from tests.data_models import AI_MAC_ADDR, DEVICE_ID, MAC_ADDR


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


@pytest.mark.asyncio
class TestSensors:
    async def test_async_setup_all_sensors_created(self, setup):
        """All sensors created"""

        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 27

    async def test_async_setup_entry_temperature_created(self, setup):
        """Sensor for device reported temperature is created on setup for non-ai controllers"""

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.TEMPERATURE
        )

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{MAC_ADDR}_{ControllerPropertyKey.TEMPERATURE}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.TEMPERATURE
        assert (
            entity.entity_description.native_unit_of_measurement
            == UnitOfTemperature.CELSIUS
        )
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (3215, 32.15), (None, 0)])
    async def test_async_update_temperature_value_correct(self, setup, value, expected):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.TEMPERATURE
        )

        test_objects.ac_infinity._controller_properties[str(DEVICE_ID)][
            ControllerPropertyKey.TEMPERATURE
        ] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_humidity_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.HUMIDITY
        )

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert (
            entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_{ControllerPropertyKey.HUMIDITY}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.HUMIDITY
        assert entity.entity_description.native_unit_of_measurement == PERCENTAGE

        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (3215, 32.15), (None, 0)])
    async def test_async_update_humidity_value_correct(self, setup, value, expected):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.HUMIDITY
        )

        test_objects.ac_infinity._controller_properties[str(DEVICE_ID)][
            ControllerPropertyKey.HUMIDITY
        ] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_vpd_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.VPD
        )

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_{ControllerPropertyKey.VPD}"
        assert entity.entity_description.device_class == SensorDeviceClass.PRESSURE
        assert (
            entity.entity_description.suggested_unit_of_measurement
            == UnitOfPressure.KPA
        )
        assert (
            entity.entity_description.native_unit_of_measurement == UnitOfPressure.KPA
        )
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (105, 1.05), (None, 0)])
    async def test_async_update_vpd_value_correct(self, setup, value, expected):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.VPD
        )

        test_objects.ac_infinity._controller_properties[str(DEVICE_ID)][
            ControllerPropertyKey.VPD
        ] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_ai_controller_temperature_created(self, setup):
        """Sensor for device reported temperature is created on setup for AI controllers"""

        entity = await execute_and_get_sensor_entity(
            setup, async_setup_entry, 7, SensorKeys.CONTROLLER_TEMPERATURE
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_7_{SensorKeys.CONTROLLER_TEMPERATURE}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.TEMPERATURE
        assert (
            entity.entity_description.native_unit_of_measurement
            == UnitOfTemperature.CELSIUS
        )
        assert entity.device_info is not None

    async def test_async_setup_entry_ai_controller_humidity_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup, async_setup_entry, 7, SensorKeys.CONTROLLER_HUMIDITY
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_7_{SensorKeys.CONTROLLER_HUMIDITY}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.HUMIDITY
        assert entity.entity_description.native_unit_of_measurement == PERCENTAGE

        assert entity.device_info is not None

    async def test_async_setup_entry_ai_controller_vpd_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup, async_setup_entry, 7, SensorKeys.CONTROLLER_VPD
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_7_{SensorKeys.CONTROLLER_VPD}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.PRESSURE
        assert (
            entity.entity_description.suggested_unit_of_measurement
            == UnitOfPressure.KPA
        )
        assert (
            entity.entity_description.native_unit_of_measurement == UnitOfPressure.KPA
        )
        assert entity.device_info is not None

    async def test_async_setup_entry_ai_probe_temperature_created(self, setup):
        """Sensor for device reported temperature is created on setup for AI controllers"""

        entity = await execute_and_get_sensor_entity(
            setup, async_setup_entry, 1, SensorKeys.PROBE_TEMPERATURE
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_1_{SensorKeys.PROBE_TEMPERATURE}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.TEMPERATURE
        assert (
            entity.entity_description.native_unit_of_measurement
            == UnitOfTemperature.CELSIUS
        )
        assert entity.device_info is not None

    async def test_async_setup_entry_ai_probe_humidity_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup, async_setup_entry, 1, SensorKeys.PROBE_HUMIDITY
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_1_{SensorKeys.PROBE_HUMIDITY}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.HUMIDITY
        assert entity.entity_description.native_unit_of_measurement == PERCENTAGE

        assert entity.device_info is not None

    async def test_async_setup_entry_ai_probe_vpd_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup, async_setup_entry, 1, SensorKeys.PROBE_VPD
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_1_{SensorKeys.PROBE_VPD}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.PRESSURE
        assert (
            entity.entity_description.suggested_unit_of_measurement
            == UnitOfPressure.KPA
        )
        assert (
            entity.entity_description.native_unit_of_measurement == UnitOfPressure.KPA
        )
        assert entity.device_info is not None

    async def test_async_setup_entry_ai_co2_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup, async_setup_entry, 2, SensorKeys.CO2_SENSOR
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_2_{SensorKeys.CO2_SENSOR}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.CO2
        assert (
            entity.entity_description.suggested_unit_of_measurement
            == CONCENTRATION_PARTS_PER_MILLION
        )
        assert (
            entity.entity_description.native_unit_of_measurement
            == CONCENTRATION_PARTS_PER_MILLION
        )
        assert entity.device_info is not None

    async def test_async_setup_entry_ai_light_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup, async_setup_entry, 2, SensorKeys.LIGHT_SENSOR
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_2_{SensorKeys.LIGHT_SENSOR}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.POWER_FACTOR
        assert entity.entity_description.suggested_unit_of_measurement == PERCENTAGE
        assert entity.entity_description.native_unit_of_measurement == PERCENTAGE
        assert entity.device_info is not None

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_entry_current_power_created_for_each_port(
        self, setup, port
    ):
        """Sensor for device port speak created on setup"""

        entity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, PortPropertyKey.SPEAK
        )

        assert (
            entity.unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{PortPropertyKey.SPEAK}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.POWER_FACTOR

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_remaining_time_for_each_port(self, setup, port):
        """Sensor for device port surplus created on setup"""

        entity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, PortPropertyKey.REMAINING_TIME
        )

        assert (
            entity.unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{PortPropertyKey.REMAINING_TIME}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.DURATION
        assert entity.device_info is not None

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_next_state_change_for_each_port(self, setup, port):
        """Sensor for device port surplus created on setup"""

        entity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, CustomPortPropertyKey.NEXT_STATE_CHANGE
        )

        assert (
            entity.unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{CustomPortPropertyKey.NEXT_STATE_CHANGE}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.TIMESTAMP
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (3, 3), (None, 0)])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_current_power_value_correct(
        self, setup, port, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._port_properties[(str(DEVICE_ID), port)][
            PortPropertyKey.SPEAK
        ] = value

        entity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, PortPropertyKey.SPEAK
        )
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortSensorEntity)
        assert entity.native_value == expected

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    @pytest.mark.parametrize("value,expected", [(0, 0), (12345, 12345), (None, 0)])
    async def test_async_update_duration_left_value_correct(
        self, setup, port, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        test_objects: ACTestObjects = setup

        entity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, PortPropertyKey.REMAINING_TIME
        )

        test_objects.ac_infinity._port_properties[(str(DEVICE_ID), port)][
            PortPropertyKey.REMAINING_TIME
        ] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortSensorEntity)
        assert entity.native_value == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    @pytest.mark.parametrize(
        "value,expected",
        [
            (500, datetime(2023, 1, 1, 0, 8, 20, tzinfo=ZoneInfo("America/Chicago"))),
            (
                12345,
                datetime(2023, 1, 1, 3, 25, 45, tzinfo=ZoneInfo("America/Chicago")),
            ),
            (None, None),
            (0, None),
        ],
    )
    @freeze_time(
        "2023-01-01 12:00:00", tz_offset=-6
    )  # Freezing time to a consistent value
    async def test_async_next_state_change_value_correct(
        self, setup, port, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        test_objects: ACTestObjects = setup

        entity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, CustomPortPropertyKey.NEXT_STATE_CHANGE
        )

        test_objects.ac_infinity._controller_properties[(str(DEVICE_ID))][
            ControllerPropertyKey.TIME_ZONE
        ] = "America/Chicago"

        test_objects.ac_infinity._port_properties[(str(DEVICE_ID), port)][
            PortPropertyKey.REMAINING_TIME
        ] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortSensorEntity)
        assert entity.native_value == expected
        test_objects.write_ha_mock.assert_called()
