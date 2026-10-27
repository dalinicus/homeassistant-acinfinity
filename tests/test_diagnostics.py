import json

import pytest
from homeassistant.components.diagnostics import REDACTED
from pytest_mock import MockFixture

from custom_components.ac_infinity.diagnostics import async_get_config_entry_diagnostics
from tests import ACTestObjects, setup_entity_mocks
from tests.data_models import DEVICE_ID, MAC_ADDR


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


@pytest.mark.asyncio
class TestDiagnostics:
    async def test_diagnostics_contains_cached_payloads(self, setup):
        test_objects: ACTestObjects = setup

        result = await async_get_config_entry_diagnostics(test_objects.hass, test_objects.config_entry)

        assert str(DEVICE_ID) in result["controller_properties"]
        assert f"{DEVICE_ID}_1" in result["device_controls"]
        assert f"{DEVICE_ID}_0" in result["device_settings"]
        # must be serializable for the download
        json.dumps(result)

    async def test_diagnostics_redacts_identifiers(self, setup):
        test_objects: ACTestObjects = setup

        result = await async_get_config_entry_diagnostics(test_objects.hass, test_objects.config_entry)
        serialized = json.dumps(result)

        assert MAC_ADDR not in serialized
        assert result["entry"]["email"] == REDACTED
        assert result["entry"]["password"] == REDACTED
        assert result["controller_properties"][str(DEVICE_ID)]["devMacAddr"] == REDACTED
