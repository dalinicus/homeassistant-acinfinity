import pytest
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)
from pytest_mock import MockFixture

from custom_components.ac_infinity.binary_sensor import (
    ACInfinityControllerBinarySensorEntity,
    ACInfinityPortBinarySensorEntity,
    async_setup_entry,
)
from custom_components.ac_infinity.const import (
    DOMAIN,
    ControllerPropertyKey,
    PortPropertyKey,
)
from custom_components.ac_infinity.core import (
    ACInfinityControllerEntity,
    ACInfinityPortEntity,
)
from tests import (
    ACTestObjects,
    execute_and_get_controller_entity,
    execute_and_get_device_entity,
    setup_entity_mocks,
)
from tests.data_models import AI_DEVICE_ID, AI_MAC_ADDR, DEVICE_ID, MAC_ADDR


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

        assert len(test_objects.entities._added_entities) == 10

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
            (PortPropertyKey.STATE, BinarySensorDeviceClass.POWER),
            (PortPropertyKey.ONLINE, BinarySensorDeviceClass.CONNECTIVITY),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_entry_entity_created_for_each_port(
        self, setup, setting, expected_class, port
    ):
        """Sensor for device port connected is created on setup"""

        sensor: ACInfinityPortEntity = await execute_and_get_device_entity(
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

    @pytest.mark.parametrize("setting", [PortPropertyKey.STATE, PortPropertyKey.ONLINE])
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
        sensor: ACInfinityPortEntity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, setting
        )

        test_objects.ac_infinity._port_properties[(str(DEVICE_ID), port)][
            setting
        ] = value

        sensor._handle_coordinator_update()

        assert isinstance(sensor, ACInfinityPortBinarySensorEntity)
        assert sensor.is_on == expected

        test_objects.write_ha_mock.assert_called()
