import pytest
from pytest_mock import MockFixture

from custom_components.ac_infinity.const import AdvancedSettingsKey, AtType, DeviceControlKey
from custom_components.ac_infinity.fan import ACInfinityDeviceFanEntity, _speed_key, async_setup_entry
from tests import ACTestObjects, execute_and_get_device_entity, setup_entity_mocks
from tests.data_models import AI_DEVICE_ID, DEVICE_ID, MAC_ADDR


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


def set_load_type(test_objects: ACTestObjects, device_id, port: int, load_type: int):
    key = (str(device_id), port)
    test_objects.service.data.device_settings[key] = {
        **test_objects.service.data.device_settings.get(key, {}),
        AdvancedSettingsKey.DEVICE_LOAD_TYPE: load_type,
    }


def set_controls(test_objects: ACTestObjects, device_id, port: int, **controls):
    key = (str(device_id), port)
    test_objects.service.data.device_controls[key] = {**test_objects.service.data.device_controls[key], **controls}


async def get_fan(setup, port: int, load_type: int = 6) -> ACInfinityDeviceFanEntity:
    set_load_type(setup, DEVICE_ID, port, load_type)
    entity = await execute_and_get_device_entity(setup, async_setup_entry, port, "fan")
    assert isinstance(entity, ACInfinityDeviceFanEntity)
    return entity


@pytest.mark.asyncio
class TestFan:
    @pytest.mark.parametrize("load_type", [0, 6])
    async def test_fan_created_for_fan_or_unset_load_type(self, setup, load_type):
        await get_fan(setup, 1, load_type)

    @pytest.mark.parametrize("load_type", [1, 8])
    async def test_fan_not_created_for_lights_or_pumps(self, setup, load_type):
        test_objects: ACTestObjects = setup
        for port in range(1, 5):
            set_load_type(test_objects, DEVICE_ID, port, load_type)

        await async_setup_entry(test_objects.hass, test_objects.config_entry, test_objects.entities.add_entities_callback)

        assert not [e for e in test_objects.entities.added_entities if MAC_ADDR in e.unique_id]

    @pytest.mark.parametrize(
        "at_type,speed,is_on,percentage",
        [(AtType.OFF, 5, False, 0), (AtType.ON, 5, True, 50), (AtType.ON, 10, True, 100), (AtType.AUTO, 3, True, 30)],
    )
    async def test_state(self, setup, at_type, speed, is_on, percentage):
        entity = await get_fan(setup, 1)
        set_controls(setup, DEVICE_ID, 1, **{DeviceControlKey.AT_TYPE: at_type, DeviceControlKey.ON_SPEED: speed})

        assert entity.is_on is is_on
        assert entity.percentage == percentage

    async def test_turn_on_with_percentage_sets_on_mode_and_speed(self, setup):
        test_objects: ACTestObjects = setup
        entity = await get_fan(setup, 2)

        await entity.async_turn_on(percentage=60)

        test_objects.port_control_sets_mock.assert_called_with(
            entity._device, {DeviceControlKey.AT_TYPE: AtType.ON, DeviceControlKey.ON_SPEED: 6}
        )

    async def test_turn_on_without_percentage_keeps_speed(self, setup):
        test_objects: ACTestObjects = setup
        entity = await get_fan(setup, 2)

        await entity.async_turn_on()

        test_objects.port_control_sets_mock.assert_called_with(entity._device, {DeviceControlKey.AT_TYPE: AtType.ON})

    @pytest.mark.parametrize("percentage,speed", [(1, 1), (15, 2), (99, 10)])
    async def test_set_percentage_rounds_up_to_a_speed(self, setup, percentage, speed):
        test_objects: ACTestObjects = setup
        entity = await get_fan(setup, 3)

        await entity.async_set_percentage(percentage)

        test_objects.port_control_sets_mock.assert_called_with(
            entity._device, {DeviceControlKey.AT_TYPE: AtType.ON, DeviceControlKey.ON_SPEED: speed}
        )

    async def test_set_percentage_zero_turns_off(self, setup):
        test_objects: ACTestObjects = setup
        entity = await get_fan(setup, 3)

        await entity.async_set_percentage(0)

        test_objects.port_control_set_mock.assert_called_with(entity._device, DeviceControlKey.AT_TYPE, AtType.OFF)

    async def test_ai_controller_uses_on_self_speed(self, setup):
        test_objects: ACTestObjects = setup
        controllers = {c.controller_id: c for c in test_objects.service.get_all_controller_properties()}
        ai_device = controllers[str(AI_DEVICE_ID)].devices[0]
        standard_device = controllers[str(DEVICE_ID)].devices[0]

        assert _speed_key(ai_device) == DeviceControlKey.ON_SELF_SPEED
        assert _speed_key(standard_device) == DeviceControlKey.ON_SPEED
