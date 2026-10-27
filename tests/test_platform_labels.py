"""Every entity must report the platform it belongs to: the keep-list form and the registry cleanup key entity
types by it, so a wrong label makes a type unselectable and its entities impossible to keep."""
import importlib

import pytest
from pytest_mock import MockFixture

from tests import ACTestObjects, setup_entity_mocks


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", ["binary_sensor", "sensor", "number", "select", "switch", "time", "fan"])
async def test_entities_report_their_own_platform(mocker: MockFixture, platform):
    test_objects: ACTestObjects = setup_entity_mocks(mocker)
    module = importlib.import_module(f"custom_components.ac_infinity.{platform}")

    await module.async_setup_entry(test_objects.hass, test_objects.config_entry, test_objects.entities.add_entities_callback)

    labels = {str(entity.platform_name) for entity in test_objects.entities.added_entities}
    # the fixture ports are pumps, so no fan entities are created; every other platform creates some
    assert labels == ({platform} if platform != "fan" else set())
