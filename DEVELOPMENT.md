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
   This starts a Home Assistant instance with the custom_components directory volume-mounted, allowing you to test changes in real-time.  Access Home Assistant at `http://localhost:8123`

### IDE Configuration

- Use VS Code with Python extension
- Configure pyright for type checking
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

### Mutually Exclusive Sensor Pairs

Some physical sensors on AI+ controllers report a single measurement in one of two units depending on device configuration (e.g. Fahrenheit vs. Celsius, µS/cm vs. mS/cm). The API exposes these as separate `sensorType` integers, but they should map to a **single Home Assistant entity** whose unit reflects whichever type the device is actually reporting.

This is achieved by giving both `SensorType` entries the **same `SensorReferenceKey`** in `SENSOR_DESCRIPTIONS`. Because the entity unique ID is derived from the reference key (not the sensor type), only one entity is ever registered for a given sensor port — whichever type is present in the sensor array passes the `suitable_fn` check, and the other is silently ignored.

**Known mutually exclusive pairs:**

| Sensor | Type A | Type B |
|--------|--------|--------|
| Temperature (probe / controller) | `PROBE_TEMPERATURE_F` (0) / `CONTROLLER_TEMPERATURE_F` (4) | `PROBE_TEMPERATURE_C` (1) / `CONTROLLER_TEMPERATURE_C` (5) |
| Hydro water temperature | `HYDRO_WATER_TEMPERATURE_F` (18) | `HYDRO_WATER_TEMPERATURE_C` (19) |
| Hydro EC | `HYDRO_EC_US` (14) — µS/cm | `HYDRO_EC_MS` (15) — mS/cm |
| Hydro TDS | `HYDRO_TDS_PPM` (16) — ppm | `HYDRO_TDS_PPT` (17) — ppt |

**Example — adding a new mutually exclusive pair:**

1. Add both sensor type constants to `SensorType` in `const.py`:
   ```python
   class SensorType:
       MY_SENSOR_UNIT_A = 42
       MY_SENSOR_UNIT_B = 43
   ```

2. Add a **single** shared reference key to `SensorReferenceKey` in `const.py`:
   ```python
   class SensorReferenceKey:
       MY_SENSOR = "mySensor"
   ```

3. Register **both** types in `SENSOR_DESCRIPTIONS` in `sensor.py` using the **same** `key` and `translation_key`:
   ```python
   SensorType.MY_SENSOR_UNIT_A: ACInfinitySensorSensorEntityDescription(
       key=SensorReferenceKey.MY_SENSOR,
       native_unit_of_measurement="unit_a",
       translation_key="my_sensor",
       ...
   ),
   SensorType.MY_SENSOR_UNIT_B: ACInfinitySensorSensorEntityDescription(
       key=SensorReferenceKey.MY_SENSOR,
       native_unit_of_measurement="unit_b",
       translation_key="my_sensor",
       ...
   ),
   ```

Only the type present in the device's sensor array at runtime will produce a live entity. If the user later reconfigures the device to report the other unit, a Home Assistant reload is required to swap the entity.

### Sensor Device Grouping

Each physical USB-C sensor accessory is represented as a child **device** in Home Assistant (visible under Settings → Devices). The grouping is determined in `ACInfinitySensor.__get_device_info` in `core.py`, which maps `sensorType` integers to a `DeviceInfo` object. Multiple sensor types from the same physical hardware share one `DeviceInfo` — keyed by a stable identifier built from `controller_id`, `sensor_port`, and a short hardware slug.

**Known sensor device groupings:**

| Physical Device | Model | Sensor Types |
|-----------------|-------|--------------|
| Probe Sensor | UIS Controller Sensor Probe (AC-SPC24) | `PROBE_TEMPERATURE_F/C` (0/1), `PROBE_HUMIDITY` (2), `PROBE_VPD` (3) |
| CO2 + Light Sensor | UIS CO2 + Light Sensor (AC-COS3) | `CO2` (11), `LIGHT` (12) |
| Water Sensor | UIS Water Sensor (AC-WDS3) | `WATER` (20) |
| Soil Sensor | UIS Soil Sensor (AC-SLS3) | `SOIL` (10) |
| Hydro Sensor | UIS Hydro Sensor (AC-HDS3) | `HYDRO_PH` (13), `HYDRO_EC_US/MS` (14/15), `HYDRO_TDS_PPM/PPT` (16/17), `HYDRO_WATER_TEMPERATURE_F/C` (18/19) |
| Controller (built-in) | — (returns the controller's own `DeviceInfo`) | `CONTROLLER_TEMPERATURE_F/C` (4/5), `CONTROLLER_HUMIDITY` (6), `CONTROLLER_VPD` (7) |

Controller-type sensor readings (types 4–7) do not create a child device — they attach directly to the controller device itself.

Unknown sensor types fall through to a catch-all that creates a generic `"Unknown Sensor"` device and logs a warning with a link to open a GitHub issue.

**When adding a new physical sensor device:**

1. Add the `SensorType` constants in `const.py`.
2. Add a new `case` block in `ACInfinitySensor.__get_device_info` in `core.py`, grouping all types that come from the same hardware under one `DeviceInfo`. The identifier slug should be lowercase and match the device's model suffix (e.g. `_hds3` for AC-HDS3).
3. Register the sensor types in `SENSOR_DESCRIPTIONS` in `sensor.py`.

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

- **Formatting**: Follow the existing code style in the repository
- **Type Hints**: `pyright` checking with Python 3.13 type annotations
- **Imports**: Keep imports organized and readable

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
# Run all tests with coverage XML report (used by SonarQube)
pytest --cov=custom_components/ac_infinity --cov-report=xml --cov-report=term

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
- `pytest --cov=custom_components/ac_infinity --cov-report=xml --cov-report=term` for testing and coverage collection
- `pyright` for type checking
- Qodana scan and quality gate to block PRs when conditions are not met
