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


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", ["select", "number", "sensor", "switch"])
async def test_kept_entities_are_never_marked_excluded(mocker: MockFixture, platform):
    """Several descriptions share a unique id (e.g. the standard, AIRTAP and room-to-room active mode selects all
    use atType).  Inapplicable variants must not be marked excluded, or the registry cleanup deletes the real,
    kept entity with the same id - which happened on a live install."""
    from custom_components.ac_infinity.const import DOMAIN
    from tests.data_models import DEVICE_ID

    test_objects: ACTestObjects = setup_entity_mocks(mocker)
    module = importlib.import_module(f"custom_components.ac_infinity.{platform}")
    entry_data = test_objects.hass.data[DOMAIN][test_objects.config_entry.entry_id]

    # first pass: learn what this controller creates, then keep all of it
    await module.async_setup_entry(test_objects.hass, test_objects.config_entry, test_objects.entities.add_entities_callback)
    kept = sorted(entry_data.available_entity_types[str(DEVICE_ID)])
    object.__setattr__(test_objects.config_entry, "data", {
        **test_objects.config_entry.data,
        "entity_filters": {str(DEVICE_ID): {"included_entity_types": kept}},
    })
    entry_data.excluded_unique_ids.clear()

    await module.async_setup_entry(test_objects.hass, test_objects.config_entry, test_objects.entities.add_entities_callback)

    created = {(str(e.platform_name), e.unique_id) for e in test_objects.entities.added_entities}
    assert created
    assert not created & entry_data.excluded_unique_ids
