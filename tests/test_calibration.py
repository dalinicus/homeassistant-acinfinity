from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.ac_infinity.calibration import async_calibrate, read_reference
from custom_components.ac_infinity.const import AdvancedSettingsKey, ControllerPropertyKey
from custom_components.ac_infinity.core import ACInfinityController, ACInfinityData, ACInfinityService
from tests.data_models import CONTROLLER_PROPERTIES, DEVICE_ID


def make_service(temp_unit: int, temperature: int, humidity: int, cal_c=0, cal_f=0, cal_h=0) -> ACInfinityService:
    service = ACInfinityService(MagicMock(), ACInfinityData())
    service.data.controller_properties[str(DEVICE_ID)] = {
        **CONTROLLER_PROPERTIES,
        ControllerPropertyKey.TEMPERATURE: temperature,
        ControllerPropertyKey.HUMIDITY: humidity,
    }
    service.data.device_settings[(str(DEVICE_ID), 0)] = {
        AdvancedSettingsKey.TEMP_UNIT: temp_unit,
        AdvancedSettingsKey.CALIBRATE_TEMP: cal_c,
        AdvancedSettingsKey.CALIBRATE_TEMP_F: cal_f,
        AdvancedSettingsKey.CALIBRATE_HUMIDITY: cal_h,
    }
    setattr(service, "update_controller_settings", AsyncMock())
    return service


def updates(service: ACInfinityService) -> AsyncMock:
    return cast(AsyncMock, service.update_controller_settings)


def controller_of(service: ACInfinityService) -> ACInfinityController:
    return service.get_all_controller_properties()[0]


@pytest.mark.asyncio
class TestCalibrate:
    async def test_celsius_controller(self):
        # reads 25.0°C with no offset, reference says 23.4°C -> offset -2 (rounded)
        service = make_service(temp_unit=1, temperature=2500, humidity=5000)
        result = await async_calibrate(service, controller_of(service), 23.4, None)

        assert result.temperature_offset == -2
        updates(service).assert_awaited_once()
        assert updates(service).call_args[0][1] == {
            AdvancedSettingsKey.CALIBRATE_TEMP: -2,
            AdvancedSettingsKey.CALIBRATE_TEMP_F: 0,
        }

    async def test_fahrenheit_controller_calibrates_in_fahrenheit(self):
        # 25.0°C = 77°F; reference 23.4°C = 74.12°F -> -3°F
        service = make_service(temp_unit=0, temperature=2500, humidity=5000)
        result = await async_calibrate(service, controller_of(service), 23.4, None)

        assert result.temperature_offset == -3
        assert updates(service).call_args[0][1] == {
            AdvancedSettingsKey.CALIBRATE_TEMP: 0,
            AdvancedSettingsKey.CALIBRATE_TEMP_F: -3,
        }

    async def test_repeat_calibration_does_not_stack(self):
        """the reading already includes the current offset; it is removed before computing the new one"""
        # raw 25.0°C, current offset -2 so it reports 23.0°C; reference still 23.4 -> offset stays -2
        service = make_service(temp_unit=1, temperature=2300, humidity=5000, cal_c=-2)
        result = await async_calibrate(service, controller_of(service), 23.4, None)

        assert result.temperature_offset == -2

    async def test_humidity_and_clamping(self):
        # reports 50% with no offset, reference 70% -> +20 clamped to the controller's +10
        service = make_service(temp_unit=1, temperature=2500, humidity=5000)
        result = await async_calibrate(service, controller_of(service), None, 70)

        assert result.humidity_offset == 10
        assert result.clamped
        assert updates(service).call_args[0][1] == {AdvancedSettingsKey.CALIBRATE_HUMIDITY: 10}

    async def test_ai_controller_rejected(self):
        service = make_service(temp_unit=1, temperature=2500, humidity=5000)
        controller = MagicMock(is_ai_controller=True, controller_name="AI")

        with pytest.raises(HomeAssistantError):
            await async_calibrate(service, controller, 23.4, None)
        updates(service).assert_not_awaited()


class TestReadReference:
    @staticmethod
    def _hass(state, unit=None):
        attributes = {"unit_of_measurement": unit} if unit else {}
        return SimpleNamespace(states=SimpleNamespace(get=lambda _: SimpleNamespace(state=state, attributes=attributes)))

    def test_fahrenheit_reference_converted_to_celsius(self):
        assert read_reference(self._hass("77", "°F"), "sensor.x", temperature=True) == pytest.approx(25.0)  # type: ignore[arg-type]

    def test_unavailable_reference_rejected(self):
        with pytest.raises(HomeAssistantError):
            read_reference(self._hass("unavailable"), "sensor.x", temperature=False)  # type: ignore[arg-type]


@pytest.mark.asyncio
class TestCalibrateAction:
    async def test_action_resolves_device_and_returns_offsets(self, mocker):
        import custom_components.ac_infinity as integration
        from custom_components.ac_infinity.const import DOMAIN

        service = make_service(temp_unit=1, temperature=2500, humidity=5000)
        entry_data = MagicMock(service=service, list_coordinator=MagicMock(async_request_refresh=AsyncMock()))
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry": entry_data}}
        hass.states.get.return_value = SimpleNamespace(state="23.4", attributes={"unit_of_measurement": "°C"})
        device_registry = MagicMock()
        device_registry.async_get.return_value = MagicMock(identifiers={(DOMAIN, str(DEVICE_ID))})
        mocker.patch.object(integration.dr, "async_get", return_value=device_registry)

        await integration.async_setup(hass, {})
        handler = hass.services.async_register.call_args[0][2]
        response = await handler(SimpleNamespace(data={"device_id": "dev", "temperature_entity": "sensor.ref"}))

        assert response == {"temperature_offset": -2, "temperature_unit": "°C", "humidity_offset": None, "clamped": False}
        entry_data.list_coordinator.async_request_refresh.assert_awaited_once()

    async def test_action_requires_a_reference(self):
        import custom_components.ac_infinity as integration

        hass = MagicMock()
        await integration.async_setup(hass, {})
        handler = hass.services.async_register.call_args[0][2]

        with pytest.raises(HomeAssistantError):
            await handler(SimpleNamespace(data={"device_id": "dev"}))
