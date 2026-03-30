# Development Guide for homeassistant-acinfinity

This guide provides comprehensive information for developers contributing to the homeassistant-acinfinity project. It covers development environment setup, architectural patterns, coding conventions, testing practices, and other important aspects of working with this Home Assistant custom component.

## Table of Contents

- [Project Overview](#project-overview)
- [Development Environment Setup](#development-environment-setup)
- [Project Architecture](#project-architecture)
- [Coding Conventions and Patterns](#coding-conventions-and-patterns)
- [Testing](#testing)
- [Contributing Guidelines](#contributing-guidelines)
- [Build and Deployment](#build-and-deployment)
- [Troubleshooting](#troubleshooting)

## Project Overview

homeassistant-acinfinity is a Home Assistant custom component (HACS integration) that enables cloud-based control and monitoring of AC Infinity smart grow tent devices. It specifically targets AC Infinity's UIS (Unified IoT System) controllers, supporting both standard controllers (69 Wifi, Pro, Pro+) and AI+ controllers with environmental sensor arrays.

The integration polls the AC Infinity cloud API and exposes device state, environmental sensors, and control settings as Home Assistant entities across multiple platforms: sensor, binary_sensor, switch, number, select, and time.

## Development Environment Setup

### Prerequisites

- Python 3.13
- Git
- Docker (for local Home Assistant development)
- A valid AC Infinity account with at least one controller

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/homeassistant-acinfinity.git
   cd homeassistant-acinfinity
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start local Home Assistant development instance:**
   ```bash
   docker-compose up homeassistant
   ```
   This starts a Home Assistant instance with the custom_components directory volume-mounted, allowing you to test changes in real-time.

### IDE Configuration

- Use VS Code with Python extension
- Configure mypy for strict type checking
- Enable ruff and black formatters
- Set up pytest for test running

### Bruno API Collection Setup

The `.bruno/` directory contains a [Bruno](https://www.usebruno.com/) API collection for exploring the AC Infinity cloud API directly. Bruno is a desktop API client — download and install it before proceeding.

1. **Open the collection in Bruno.** In the Bruno application, click **Open Collection** and select the `.bruno/` folder from the repository root.

2. **Configure the environment.** In Bruno, open the **Environments** panel and select the `default` environment. Set your credentials as secret variables:
   - `EMAIL` — your AC Infinity account email
   - `PASSWORD` — your AC Infinity account password

3. **Run the `Login` request.** The response payload will include an `appId` field. Copy this value and set `USER_ID` in the environment to that value. This ID is used as the API key (`token` header) for all subsequent requests.

4. **Run the `Get Devices List` request.** This returns all controllers on your account. From the response, locate and set the following environment variables:
   - `DEVICE_ID` — device ID of a standard (non-AI+) controller
   - `AI_DEVICE_ID` — device ID of an AI+ controller

Once populated, the full collection of requests can be used to inspect real API payloads when developing or debugging.

### Testing Your Setup

1. Add the integration through Home Assistant UI (Settings → Devices & Services → Add Integration → AC Infinity)
2. Use your AC Infinity account credentials
3. Verify entities appear and update correctly

## Project Architecture

### High-Level Design

The integration follows a layered architecture:

```
Home Assistant Entity Platforms
    ↓
Entity Layer (core.py)
    ↓
Service Layer (core.py)
    ↓
HTTP Client Layer (client.py)
```

### Component Structure

```
custom_components/ac_infinity/
├── __init__.py          # Integration entry point and lifecycle
├── client.py            # Async aiohttp client for AC Infinity API
├── core.py              # Data models, service layer, coordinator, entity base classes
├── const.py             # All constants and API field definitions
├── config_flow.py       # ConfigFlow and OptionsFlow implementations
├── manifest.json        # Integration metadata
├── strings.json         # UI labels and translations
├── translations/        # Localized strings
├── binary_sensor.py     # Binary sensor platform
├── sensor.py            # Sensor platform
├── switch.py            # Switch platform
├── select.py            # Select platform
├── number.py            # Number platform
└── time.py              # Time platform
```

### Data Model Hierarchy

The integration uses a three-level object hierarchy:

1. **ACInfinityController**: Represents one physical UIS hub (identified by MAC address)
   - Contains device list and sensor arrays (AI+ only)
   - Manages controller-level properties

2. **ACInfinityDevice**: Represents one USB-C port on a controller
   - Tracks port-specific state and settings
   - Handles device online status and control

3. **ACInfinitySensor**: Represents environmental sensor arrays (AI+ controllers only)
   - Manages sensor readings (temperature, humidity, CO2, etc.)
   - Connected via USB-C ports

### Entity Architecture

All entities extend `CoordinatorEntity[ACInfinityDataUpdateCoordinator]` with specialized base classes:

- **ACInfinityControllerEntity**: Per-controller entities
- **ACInfinityDeviceEntity**: Per-port device entities  
- **ACInfinitySensorEntity**: Per-sensor entities

### Service Layer

The `ACInfinityService` serves as the data management layer within Home Assistant's coordinator pattern:

- **Data Caching**: Stores API responses in structured dictionaries to minimize redundant API calls
- **Coordinator Integration**: Called by `ACInfinityDataUpdateCoordinator` during refresh cycles to update cached data
- **Entity Query Interface**: Provides typed accessor methods that entity description callbacks use to retrieve current values
- **Update Operations**: Handles write operations to the AC Infinity API with retry logic and error handling

### API Client

The `ACInfinityClient` handles all HTTP communication:

- Async aiohttp-based requests
- Handles authentication and session management
- Accounts for API quirks
- Supports both standard and AI+ controller endpoints

## Coding Conventions and Patterns

### Constants Management

All API field names are centralized in `const.py` using plain Python classes:

```python
class ControllerPropertyKey:
    DEVICE_ID = "devId"
    MAC_ADDR = "devMacAddr"
    DEVICE_NAME = "devName"

class DevicePropertyKey:
    PORT = "port"
    NAME = "portName"
    ONLINE = "online"
    STATE = "loadState"
```

**Rule**: Never hardcode API field strings outside `const.py`.

### Unique Identifier Format

Entity unique IDs follow a consistent pattern:
```
{domain}_{mac_address}_{port_specifier}_{data_key}
```

Examples:
- `ac_infinity_2B120D62DC00_temperature` (controller-level, no port specifier)
- `ac_infinity_2B120D62DC00_port_1_loadState` (device on port 1)
- `ac_infinity_2B120D62DC00_sensor_1_co2Sensor` (sensor on port 1)

### Controller Family Handling

The integration supports two distinct API patterns:

| Family | Detection | Update Method |
|--------|-----------|---------------|
| Standard | `is_ai_controller == False` | `update_device_settings` |
| AI | `is_ai_controller == True` | `update_ai_device_control_and_settings` |

### Entity Description Pattern

Each platform uses frozen dataclasses with mixins:

```python
@dataclass(frozen=True)
class ACInfinityDeviceSensorEntityDescription(
    ACInfinitySensorEntityDescription,
    ACInfinityDeviceReadOnlyMixin
):
    key: str
    enabled_fn: Callable[[ConfigEntry, str, str], bool]
    suitable_fn: Callable[[ACInfinityEntity, ACInfinityDevice], bool]
    get_value_fn: Callable[[ACInfinityEntity, ACInfinityDevice], Any]
    at_type_fn: Callable[[int], bool] | None  # Optional mode filtering
    # HA metadata...
```

Note: Callback signatures vary by entity scope:
- Controller entities: `suitable_fn` takes `ACInfinityController`, `get_value_fn` takes `ACInfinityController`
- Device entities: `suitable_fn` takes `ACInfinityDevice`, `get_value_fn` takes `ACInfinityDevice`
- Sensor entities: `suitable_fn` takes `ACInfinitySensor`, `get_value_fn` takes `ACInfinitySensor`

### Style Guidelines

- **Quotes**: Single quotes preferred (`ruff Q000`)
- **Linting**: `ruff` as primary linter with custom rules in `pyproject.toml`
- **Formatting**: `black` for consistent formatting
- **Type Hints**: Strict mypy checking with Python 3.13 type annotations
- **Imports**: Organized and linted automatically

### Naming Conventions

- Class names: `PascalCase`
- Method names: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private members: Leading underscore
- API keys: Exact API field names (even if misspelled)

## Testing

### Test Infrastructure

Tests use a comprehensive mocking setup in `tests/__init__.py`:

- `setup_entity_mocks()`: Factory for test environment
- Query helpers for retrieving specific entities
- Pre-configured coordinator and service layer

### Test Data

Raw test constants in `tests/data_models.py`:
- Device identifiers and configuration
- Mock API response fixtures (DEVICE_PROPERTY_ONE through FOUR for different ports)
- Complete config entry structures

### Testing Patterns

```python
@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)

@pytest.mark.asyncio
async def test_entity_value(setup):
    entity = await execute_and_get_device_entity(
        setup, async_setup_entry, port=1, data_key="loadState"
    )
    assert entity.native_value == expected_value
```

### Mocking Tools

- `pytest-mock`: For general mocking
- `aioresponses`: For HTTP request mocking
- `freezegun`: For time-sensitive tests
- `pytest-asyncio`: For async test support

### Running Tests

```bash
# Run all tests with coverage
pytest --cov

# Run specific test file
pytest tests/test_sensor.py -v

# Run with verbose output
pytest -v
```

## Build and Deployment

### Version Management

- Versions follow semantic versioning (current: 2.1.1)
- Update `manifest.json` version field on releases
- Update changelog in repository

### HACS Integration

- Integration is published via HACS
- `hacs.json` contains metadata
- Releases trigger HACS updates

### CI/CD

GitHub Actions runs:
- `pytest --cov` for testing
- `ruff check` for linting
- `mypy` for type checking
- Coverage reporting

Access Home Assistant at `http://localhost:8123`