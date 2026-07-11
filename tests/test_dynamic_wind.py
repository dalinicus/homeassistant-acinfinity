from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.ac_infinity import switch as switch_module
from custom_components.ac_infinity.const import AdvancedSettingsKey


PORT_PARAM_DATA_OFF = "[0, 2, 1, 2, 19, 136, 2, 1, 0]"
PORT_PARAM_DATA_ON = "[0, 2, 1, 2, 19, 136, 2, 1, 1]"


def _create_test_objects(
    port_param_data=PORT_PARAM_DATA_OFF,
    *,
    load_type=6,
    is_ai_controller=False,
):
    controller = SimpleNamespace(
        controller_id="controller-id",
        is_ai_controller=is_ai_controller,
    )
    device = SimpleNamespace(controller=controller, device_port=2)

    service = Mock()

    def get_device_setting(_controller_id, _device_port, setting_key, default=None):
        if setting_key == AdvancedSettingsKey.DEVICE_LOAD_TYPE:
            return load_type
        if setting_key == AdvancedSettingsKey.PORT_PARAM_DATA:
            return port_param_data
        return default

    service.get_device_setting.side_effect = get_device_setting
    service.update_device_setting = AsyncMock()
    entity = SimpleNamespace(ac_infinity=service)
    return entity, device, service


def test_parse_port_param_data():
    assert switch_module._parse_port_param_data(PORT_PARAM_DATA_ON)[8] == 1
    assert switch_module._parse_port_param_data([0, 2, 1, 2, 19, 136, 2, 1, 0])[8] == 0
    assert switch_module._parse_port_param_data("not-json") is None
    assert switch_module._parse_port_param_data("[0, 1]") is None
    assert switch_module._parse_port_param_data("[0,1,2,3,4,5,6,7,8,9]") is None


def test_dynamic_wind_suitability():
    entity, device, _service = _create_test_objects()
    assert switch_module.__suitable_fn_dynamic_wind(entity, device)

    entity, device, _service = _create_test_objects(load_type=1)
    assert not switch_module.__suitable_fn_dynamic_wind(entity, device)

    entity, device, _service = _create_test_objects("invalid")
    assert not switch_module.__suitable_fn_dynamic_wind(entity, device)

    entity, device, _service = _create_test_objects(is_ai_controller=True)
    assert not switch_module.__suitable_fn_dynamic_wind(entity, device)


@pytest.mark.parametrize(
    ("port_param_data", "expected"),
    [
        (PORT_PARAM_DATA_ON, True),
        (PORT_PARAM_DATA_OFF, False),
        ("invalid", None),
    ],
)
def test_dynamic_wind_state(port_param_data, expected):
    entity, device, _service = _create_test_objects(port_param_data)
    assert switch_module.__get_value_fn_dynamic_wind(entity, device) is expected


@pytest.mark.asyncio
async def test_dynamic_wind_write_preserves_other_parameters():
    entity, device, service = _create_test_objects(PORT_PARAM_DATA_OFF)

    await switch_module.__set_value_fn_dynamic_wind(entity, device, 1)

    service.update_device_setting.assert_awaited_once_with(
        device,
        AdvancedSettingsKey.PORT_PARAM_DATA,
        "[0,2,1,2,19,136,2,1,1]",
    )


@pytest.mark.asyncio
async def test_dynamic_wind_write_rejects_invalid_data():
    entity, device, service = _create_test_objects("invalid")

    with pytest.raises(ValueError, match="Invalid portParamData"):
        await switch_module.__set_value_fn_dynamic_wind(entity, device, 1)

    service.update_device_setting.assert_not_awaited()
