# Copilot Instructions — homeassistant-acinfinity

Home Assistant custom component (HACS) for [AC Infinity](https://acinfinity.com/) UIS smart grow tent controllers. The integration polls the AC Infinity cloud API and exposes device state and settings as Home Assistant entities.

## Build & Test Commands

```bash
# Run all tests
pytest --cov

# Run a single test file
pytest tests/test_sensor.py -v

# Lint
ruff check custom_components/ tests/

# Format
black custom_components/ tests/

# Type check
mypy custom_components/ac_infinity/

# Start local HA dev instance (volume-mounts custom_components/)
docker-compose up homeassistant
```

Dependencies: `pip install -r requirements.txt` (Python 3.13)

## Architecture

```
custom_components/ac_infinity/
  client.py       – async aiohttp HTTP client for the AC Infinity cloud API
  core.py         – data models, entity base classes, coordinator, service layer
  const.py        – all constants and API key classes
  config_flow.py  – ConfigFlow + OptionsFlow (email/password + entity-enable options)
  binary_sensor.py / sensor.py / select.py / number.py / time.py / switch.py
                  – HA platform setup + entity descriptions per platform
  strings.json / translations/  – UI strings
```

### Data model hierarchy

```
ACInfinityController   — one physical UIS hub (identified by MAC address)
  └── ACInfinityDevice — one USB-C port on the controller (with or without a device)
  └── ACInfinitySensor — environmental sensor array (AI+controller only)
```

### Entity base classes (`core.py`)

All entities extend `CoordinatorEntity[ACInfinityDataUpdateCoordinator]`:

| Class | Scope |
|---|---|
| `ACInfinityControllerEntity` | per-controller |
| `ACInfinityDeviceEntity` | per-port device |
| `ACInfinitySensorEntity` | per-sensor (AI+) |

### Unique ID format

`{domain}_{mac_addr}_{port_N | sensor_N | controller_key}_{data_key}`

## Coding Conventions

### Constants (`const.py`)

- All API field names live in plain classes (not `Enum`): `ControllerPropertyKey`, `DevicePropertyKey`, `DeviceControlKey`, `SensorPropertyKey`, `AdvancedSettingsKey`, `CustomDevicePropertyKey`, `SensorReferenceKey`.
- User-facing config keys: `ConfigurationKey`. Entity enable choices: `EntityConfigValue`.
- Never hard-code API field strings outside `const.py`.

### Entity descriptions

Each platform uses a `@dataclass(frozen=True)` description class that carries:
- `key` — matches the corresponding const key
- a value-accessor callback (lambda over `ACInfinityService`)
- HA-specific metadata (device class, unit, state class, etc.)

### Two controller families

| Family | Detection | API differences |
|---|---|---|
| Standard (69 Wifi, Pro, Pro+) | `controller.is_ai_controller == False` | `update_device_settings` |
| AI+ | `controller.is_ai_controller == True` | `update_ai_device_control_and_settings`; has `sensors` array |

### API client quirks

- AC Infinity's API truncates passwords to 25 characters; `client.py` mirrors this.
- `BINARY_SENSOR` platform must load first (creates HA devices that subsequent platforms reference via `via_device`).

### Linting / style

- Single quotes preferred (`ruff Q000`).
- `ruff` is the primary linter (see `pyproject.toml` for the full rule set); `black` for formatting.
- `mypy` strict-ish; Python 3.13 type hints.

## Testing Patterns

Tests mirror component files: `tests/test_<platform>.py` ↔ `custom_components/ac_infinity/<platform>.py`.

### Shared infrastructure (`tests/__init__.py`, `tests/data_models.py`)

- `setup_entity_mocks(mocker)` — sets up a fully mocked HA environment; returns `ACTestObjects`.
- `execute_and_get_controller_entity(setup, async_setup_entry, property_key)` — runs `async_setup_entry` and returns the matching `ACInfinityControllerEntity`.
- `execute_and_get_device_entity(setup, async_setup_entry, port, data_key)` — same for `ACInfinityDeviceEntity`.
- `execute_and_get_sensor_entity(setup, async_setup_entry, port, data_key)` — same for `ACInfinitySensorEntity`.
- `data_models.py` holds raw test constants (not pytest fixtures): `MAC_ADDR`, `AI_MAC_ADDR`, `DEVICE_ID`, `AI_DEVICE_ID`, `DEVICE_PROPERTIES_DATA`, `DEVICE_CONTROLS_DATA`, etc.

### Typical test pattern

```python
@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)

@pytest.mark.asyncio
async def test_entity_value(setup):
    entity = await execute_and_get_device_entity(
        setup, async_setup_entry, port=1, data_key="some_key"
    )
    assert entity.native_value == expected_value
```

- Use `pytest-mock` (`MockFixture`), `AsyncMock` / `MagicMock`.
- Use `aioresponses` to mock `aiohttp` HTTP calls.
- Use `freezegun` (`@freeze_time`) for time-sensitive tests.
- Tests are `async` via `pytest-asyncio` (`asyncio_default_fixture_loop_scope = "function"`).
