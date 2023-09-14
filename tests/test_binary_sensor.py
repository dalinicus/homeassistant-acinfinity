import pytest
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)
from pytest_mock import MockFixture

from custom_components.ac_infinity.binary_sensor import (
    ACInfinityPortBinarySensorEntity,
    async_setup_entry,
)
from custom_components.ac_infinity.const import (
    DOMAIN,
    SENSOR_PORT_KEY_ONLINE,
)
from custom_components.ac_infinity.sensor import ACInfinityPortSensorEntity
from tests import (
    ACTestObjects,
    execute_and_get_port_entity,
    setup_entity_mocks,
)
from tests.data_models import MAC_ADDR


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
            test_objects.configEntry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 4

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_entry_plug_created_for_each_port(self, setup, port):
        """Sensor for device port connected is created on setup"""

        sensor: ACInfinityPortSensorEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, SENSOR_PORT_KEY_ONLINE
        )

        assert "Status" in sensor._attr_name
        assert (
            sensor._attr_unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{SENSOR_PORT_KEY_ONLINE}"
        )
        assert sensor._attr_device_class == BinarySensorDeviceClass.PLUG

    @pytest.mark.parametrize(
        "port,expected",
        [
            (1, True),
            (2, True),
            (3, True),
            (4, False),
        ],
    )
    async def test_async_update_plug_value_Correct(self, setup, port, expected):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        sensor: ACInfinityPortBinarySensorEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, SENSOR_PORT_KEY_ONLINE
        )
        sensor._handle_coordinator_update()

        assert sensor.is_on == expected
        test_objects.write_ha_mock.assert_called()
