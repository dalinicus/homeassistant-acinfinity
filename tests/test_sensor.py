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
    ControllerPropertyKey,
    PortPropertyKey,
    PortSettingKey,
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
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 11

    async def test_async_setup_entry_temperature_created(self, setup):
        """Sensor for device reported temperature is created on setup"""

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

    async def test_async_update_temperature_value_correct(self, setup):
        """Reported sensor value matches the value in the json payload"""

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.TEMPERATURE
        )
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert entity.native_value == 24.17

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

    async def test_async_update_humidity_value_correct(self, setup):
        """Reported sensor value matches the value in the json payload"""

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.HUMIDITY
        )
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert entity.native_value == 72

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

    async def test_async_update_vpd_value_correct(self, setup):
        """Reported sensor value matches the value in the json payload"""

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.VPD
        )
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert entity.native_value == 0.83

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_entry_current_power_created_for_each_port(
        self, setup, port
    ):
        """Sensor for device port speak created on setup"""

        entity = await execute_and_get_port_entity(
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

        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, PortSettingKey.SURPLUS
        )

        assert (
            entity.unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{PortSettingKey.SURPLUS}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.DURATION
        assert entity.device_info is not None

    @pytest.mark.parametrize(
        "port,expected",
        [
            (1, 5),
            (2, 7),
            (3, 5),
            (4, 0),
        ],
    )
    async def test_async_update_current_power_value_correct(
        self, setup, port, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._port_settings[(str(DEVICE_ID), port)][
            PortPropertyKey.SPEAK
        ] = expected
        entity = await execute_and_get_port_entity(
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

        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, PortSettingKey.SURPLUS
        )

        test_objects.ac_infinity._port_settings[(str(DEVICE_ID), port)][
            PortSettingKey.SURPLUS
        ] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortSensorEntity)
        assert entity.native_value == expected
        test_objects.write_ha_mock.assert_called()
