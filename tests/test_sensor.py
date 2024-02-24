import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
)
from pytest_mock import MockFixture

from custom_components.ac_infinity.const import (
    DOMAIN,
    SENSOR_KEY_HUMIDITY,
    SENSOR_KEY_TEMPERATURE,
    SENSOR_KEY_VPD,
    SENSOR_PORT_KEY_SPEAK,
    SENSOR_SETTING_KEY_SURPLUS,
)
from custom_components.ac_infinity.sensor import (
    ACInfinityControllerSensorEntity,
    ACInfinityPortSensorEntity,
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
class TestSensors:
    async def test_async_setup_all_sensors_created(self, setup):
        """All sensors created"""

        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.configEntry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 11

    async def test_async_setup_entry_temperature_created(self, setup):
        """Sensor for device reported temperature is created on setup"""

        sensor: ACInfinityControllerSensorEntity = (
            await execute_and_get_controller_entity(
                setup, async_setup_entry, SENSOR_KEY_TEMPERATURE
            )
        )

        assert sensor.unique_id == f"{DOMAIN}_{MAC_ADDR}_{SENSOR_KEY_TEMPERATURE}"
        assert sensor.entity_description.device_class == SensorDeviceClass.TEMPERATURE
        assert (
            sensor.entity_description.native_unit_of_measurement
            == UnitOfTemperature.CELSIUS
        )
        assert sensor.device_info is not None

    async def test_async_update_temperature_value_Correct(self, setup):
        """Reported sensor value matches the value in the json payload"""

        sensor: ACInfinityControllerSensorEntity = (
            await execute_and_get_controller_entity(
                setup, async_setup_entry, SENSOR_KEY_TEMPERATURE
            )
        )
        sensor._handle_coordinator_update()

        assert sensor.native_value == 24.17

    async def test_async_setup_entry_humidity_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        sensor: ACInfinityControllerSensorEntity = (
            await execute_and_get_controller_entity(
                setup, async_setup_entry, SENSOR_KEY_HUMIDITY
            )
        )

        assert sensor.unique_id == f"{DOMAIN}_{MAC_ADDR}_{SENSOR_KEY_HUMIDITY}"
        assert sensor.entity_description.device_class == SensorDeviceClass.HUMIDITY
        assert sensor.entity_description.native_unit_of_measurement == PERCENTAGE

        assert sensor.device_info is not None

    async def test_async_update_humidity_value_Correct(self, setup):
        """Reported sensor value matches the value in the json payload"""

        sensor: ACInfinityControllerSensorEntity = (
            await execute_and_get_controller_entity(
                setup, async_setup_entry, SENSOR_KEY_HUMIDITY
            )
        )
        sensor._handle_coordinator_update()

        assert sensor.native_value == 72

    async def test_async_setup_entry_vpd_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        sensor: ACInfinityControllerSensorEntity = (
            await execute_and_get_controller_entity(
                setup, async_setup_entry, SENSOR_KEY_VPD
            )
        )

        assert sensor.unique_id == f"{DOMAIN}_{MAC_ADDR}_{SENSOR_KEY_VPD}"
        assert sensor.entity_description.device_class == SensorDeviceClass.PRESSURE
        assert (
            sensor.entity_description.suggested_unit_of_measurement
            == UnitOfPressure.KPA
        )
        assert (
            sensor.entity_description.native_unit_of_measurement == UnitOfPressure.KPA
        )
        assert sensor.device_info is not None

    async def test_async_update_vpd_value_Correct(self, setup):
        """Reported sensor value matches the value in the json payload"""

        sensor: ACInfinityControllerSensorEntity = (
            await execute_and_get_controller_entity(
                setup, async_setup_entry, SENSOR_KEY_VPD
            )
        )
        sensor._handle_coordinator_update()

        assert sensor.native_value == 0.83

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_entry_current_power_created_for_each_port(
        self, setup, port
    ):
        """Sensor for device port speak created on setup"""

        sensor: ACInfinityPortSensorEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, SENSOR_PORT_KEY_SPEAK
        )

        assert (
            sensor.unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{SENSOR_PORT_KEY_SPEAK}"
        )
        assert sensor.entity_description.device_class == SensorDeviceClass.POWER_FACTOR

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_remaining_time_for_each_port(self, setup, port):
        """Sensor for device port surplus created on setup"""

        sensor: ACInfinityPortSensorEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, SENSOR_SETTING_KEY_SURPLUS
        )

        assert (
            sensor.unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{SENSOR_SETTING_KEY_SURPLUS}"
        )
        assert sensor.entity_description.device_class == SensorDeviceClass.DURATION
        assert sensor.device_info is not None

    @pytest.mark.parametrize(
        "port,expected",
        [
            (1, 5),
            (2, 7),
            (3, 5),
            (4, 0),
        ],
    )
    async def test_async_update_current_power_value_Correct(
        self, setup, port, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._port_settings[str(DEVICE_ID)][port][
            SENSOR_PORT_KEY_SPEAK
        ] = expected
        sensor: ACInfinityPortSensorEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, SENSOR_PORT_KEY_SPEAK
        )
        sensor._handle_coordinator_update()

        assert sensor.native_value == expected

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    @pytest.mark.parametrize("value,expected", [(0, 0), (12345, 12345), (None, 0)])
    async def test_async_update_duration_left_value_Correct(
        self, setup, port, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        test_objects: ACTestObjects = setup

        sensor: ACInfinityPortSensorEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, SENSOR_SETTING_KEY_SURPLUS
        )

        test_objects.ac_infinity._port_settings[str(DEVICE_ID)][port][
            SENSOR_SETTING_KEY_SURPLUS
        ] = value
        sensor._handle_coordinator_update()

        assert sensor.native_value == expected
        test_objects.write_ha_mock.assert_called()
