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
    PortPropertyKey,
)
from custom_components.ac_infinity.core import ACInfinityPortEntity
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
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 4

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_entry_plug_created_for_each_port(self, setup, port):
        """Sensor for device port connected is created on setup"""

        sensor: ACInfinityPortEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, PortPropertyKey.ONLINE
        )

        assert (
            sensor.unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{PortPropertyKey.ONLINE}"
        )
        assert sensor.entity_description.device_class == BinarySensorDeviceClass.PLUG
        assert sensor.device_info is not None

    @pytest.mark.parametrize(
        "port,expected",
        [
            (1, True),
            (2, True),
            (3, True),
            (4, False),
        ],
    )
    async def test_async_update_plug_value_correct(self, setup, port, expected):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        sensor: ACInfinityPortEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, PortPropertyKey.ONLINE
        )
        sensor._handle_coordinator_update()

        assert isinstance(sensor, ACInfinityPortBinarySensorEntity)
        assert sensor.is_on == expected

        test_objects.write_ha_mock.assert_called()
