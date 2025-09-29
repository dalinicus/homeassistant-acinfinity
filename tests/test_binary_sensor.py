import pytest
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)
from homeassistant.components.sensor import SensorDeviceClass
from pytest_mock import MockFixture

from custom_components.ac_infinity.binary_sensor import (
    ACInfinityControllerBinarySensorEntity,
    ACInfinityDeviceBinarySensorEntity,
    ACInfinitySensorBinarySensorEntity,
    async_setup_entry,
)
from custom_components.ac_infinity.const import (
    DOMAIN,
    ControllerPropertyKey,
    DevicePropertyKey,
    SensorPropertyKey,
    SensorReferenceKey,
    SensorType,
)
from custom_components.ac_infinity.core import (
    ACInfinityControllerEntity,
    ACInfinityDeviceEntity,
)
from tests import (
    ACTestObjects,
    execute_and_get_controller_entity,
    execute_and_get_device_entity,
    execute_and_get_sensor_entity,
    setup_entity_mocks,
)
from tests.data_models import (
    AI_DEVICE_ID,
    AI_MAC_ADDR,
    DEVICE_ID,
    MAC_ADDR,
    WATER_SENSOR_PORT,
)


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


@pytest.mark.asyncio
class TestBinarySensors:
    async def test_async_setup_all_sensors_created(self, setup):
        """All sensors created"""
        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 11

    async def test_async_setup_entry_entity_created_for_controller(self, setup):
        """Sensor for device port connected is created on setup"""

        sensor: ACInfinityControllerEntity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.ONLINE
        )

        assert sensor.unique_id == f"{DOMAIN}_{MAC_ADDR}_{ControllerPropertyKey.ONLINE}"
        assert (
            sensor.entity_description.device_class
            == BinarySensorDeviceClass.CONNECTIVITY
        )
        assert sensor.device_info is not None

    @pytest.mark.parametrize(
        "setting, expected_class",
        [
            (DevicePropertyKey.STATE, BinarySensorDeviceClass.POWER),
            (DevicePropertyKey.ONLINE, BinarySensorDeviceClass.CONNECTIVITY),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_entry_entity_created_for_each_port(
        self, setup, setting, expected_class, port
    ):
        """Sensor for device port connected is created on setup"""

        sensor: ACInfinityDeviceEntity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, setting
        )

        assert sensor.unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{setting}"
        assert sensor.entity_description.device_class == expected_class
        assert sensor.device_info is not None

    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, False),
            (0, False),
            (1, True),
        ],
    )
    @pytest.mark.parametrize(
        "device_id,mac", [(DEVICE_ID, MAC_ADDR), (AI_DEVICE_ID, AI_MAC_ADDR)]
    )
    async def test_async_update_entity_controller_value_correct(
        self, setup, value, expected, device_id, mac
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        sensor: ACInfinityControllerEntity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.ONLINE, mac
        )

        test_objects.ac_infinity._controller_properties[str(device_id)][
            ControllerPropertyKey.ONLINE
        ] = value

        sensor._handle_coordinator_update()

        assert isinstance(sensor, ACInfinityControllerBinarySensorEntity)
        assert sensor.is_on == expected

        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize("setting", [DevicePropertyKey.STATE, DevicePropertyKey.ONLINE])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, False),
            (0, False),
            (1, True),
        ],
    )
    async def test_async_update_entity_port_value_correct(
        self, setup, port, setting, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        sensor: ACInfinityDeviceEntity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, setting
        )

        test_objects.ac_infinity._device_properties[(str(DEVICE_ID), port)][
            setting
        ] = value

        sensor._handle_coordinator_update()

        assert isinstance(sensor, ACInfinityDeviceBinarySensorEntity)
        assert sensor.is_on == expected

        test_objects.write_ha_mock.assert_called()

    async def test_async_setup_entry_ai_water_sensor_created(self, setup):
        """Sensor for device reported water detected is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            WATER_SENSOR_PORT,
            SensorReferenceKey.WATER,
        )

        assert isinstance(entity, ACInfinitySensorBinarySensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_{WATER_SENSOR_PORT}_{SensorReferenceKey.WATER}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.MOISTURE
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, False), (1, True), (None, False)])
    async def test_async_update_ai_soil_sensor_value_correct(
        self, setup, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            WATER_SENSOR_PORT,
            SensorReferenceKey.WATER,
        )

        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), WATER_SENSOR_PORT, SensorType.WATER)
        ][SensorPropertyKey.SENSOR_DATA] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinitySensorBinarySensorEntity)
        assert entity.is_on == expected
