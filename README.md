# THANKS to Pierre Herbert 
This software is a fork of https://github.com/pierrehebert/photovoltaic_optimizer, under APACHE LICENCE
The fork consists in using power consumption metrics pushed on an mqtt topic instead of using a built in power capacity data collection.
It also optimize some equipments with for exemple temperature driven equipment.

 Please read https://www.pierrox.net/wordpress/2019/02/15/optimisation-photovoltaique-1-le-raisonnement/ (French) for background on the project.

# Photovoltaic Power Optimization System

This project implements a power regulation system for optimizing photovoltaic energy consumption.

The system monitors power production and consumption, dynamically allocating power to various equipment to maximize the use of available photovoltaic energy. It supports different types of equipment with varying power consumption profiles and control mechanisms.

## Repository Structure

```
.
├── config.py
├── debug.py
├── equipment_config.yml
├── equipment_loader.py
├── equipment.py
├── power_regulation.py
├── README_equipment_config.md
└── README.md
```

### Key Files:

- `power_regulation.py`: Main power regulation loop
- `equipment.py`: Defines equipment classes and behaviors
- `equipment_loader.py`: Loads equipment configurations from YAML
- `config.py`: Configuration settings for MQTT and InfluxDB
- `equipment_config.yml`: YAML configuration for equipment

## Usage Instructions

### Prerequisites

- Python 3.x
- MQTT broker (e.g., Mosquitto)
- InfluxDB

### Installation

1. Clone the repository:
   ```
   git clone <repository_url>
   cd <repository_directory>
   ```

2. Install required Python packages:
   ```
   pip install paho-mqtt influxdb pytz pyyaml
   ```

3. Configure MQTT and InfluxDB settings in `config.py` or set corresponding environment variables.

4. Set up your equipment in `equipment_config.yml`.

### Running the System

Execute the main regulation script:

```
python power_regulation.py
```

### Configuration

#### MQTT Settings

Modify `config.py` or set environment variables:

```python
MQTT_BROKER_HOST = 'localhost'
MQTT_BROKER_PORT = 1883
MQTT_KEEPALIVE = 120
MQTT_USERNAME = 'your_username'
MQTT_PASSWORD = 'your_password'
```

#### InfluxDB Settings

```python
INFLUXDB_HOST = 'localhost'
INFLUXDB_PORT = 8086
INFLUXDB_DATABASE = 'teleinfo'
INFLUXDB_USERNAME = 'your_username'
INFLUXDB_PASSWORD = 'your_password'
```

#### Equipment Configuration

Define equipment in `equipment_config.yml`:

```yaml
equipment:
  - name: water_heater
    type: TempDrivenVariablePowerEquipment
    max_power: 2400
    temp_min: 45
    temp_eco: 50
    temp_sol_min: 55
    temp_max: 60
```

### Troubleshooting

1. MQTT Connection Issues:
   - Ensure the MQTT broker is running and accessible
   - Verify MQTT credentials in `config.py`
   - Check firewall settings

2. InfluxDB Connection Errors:
   - Confirm InfluxDB is running and accessible
   - Verify InfluxDB credentials and database name in `config.py`

3. Equipment Not Responding:
   - Check equipment configuration in `equipment_config.yml`
   - Verify MQTT topics for equipment control

For detailed logging, modify the log level in `debug.py`:

```python
logger.setLevel(logging.DEBUG)
ch.setLevel(logging.DEBUG)
```

## Data Flow

The power regulation system operates as follows:

1. Power measurements are received via MQTT topics:
   - Injected power: `tic/SINSTI`
   - Consumed power: `tic/SINSTS`
   - Reactive power: `tic/ERQT`

2. The `evaluate()` function in `power_regulation.py` processes these measurements.

3. Based on the current power balance, the system decides to increase or decrease power allocation to equipment.

4. Equipment control commands are sent via MQTT to the respective devices.

5. Power and energy data are stored in InfluxDB for monitoring and analysis.

```
[MQTT Broker] <-> [power_regulation.py] <-> [InfluxDB]
       ^                    |
       |                    v
[Equipment Control]    [Equipment Classes]
```

## Infrastructure

This project primarily consists of Python scripts and does not have a dedicated infrastructure stack. However, it relies on the following external services:

- MQTT Broker: For real-time communication of power measurements and equipment control
- InfluxDB: Time-series database for storing power and energy data

Ensure these services are properly set up and configured in your environment.