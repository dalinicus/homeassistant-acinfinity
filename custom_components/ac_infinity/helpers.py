from .const import SENSOR_PORT_PREFIX


def assemble_port_sensor_key(portNumber: int, sensorKey: str):
    return f"{SENSOR_PORT_PREFIX}_{portNumber}_{sensorKey}"
