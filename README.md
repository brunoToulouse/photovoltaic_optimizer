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
├── teleinfo.py
├── README_equipment_config.md
├── README_RASPBERRY_PI.md
└── README.md
```

### Key Files:

- `power_regulation.py`: Main power regulation loop
- `equipment.py`: Defines equipment classes and behaviors
- `equipment_loader.py`: Loads equipment configurations from YAML
- `config.py`: Configuration settings for MQTT and InfluxDB
- `equipment_config.yml`: YAML configuration for equipment
- `teleinfo.py`: Teleinfo data reader for French smart meters (Linky)
- `README_RASPBERRY_PI.md`: Complete Raspberry Pi setup guide

## Usage Instructions

### Prerequisites

- Python 3.x
- MQTT broker (e.g., Mosquitto)
- InfluxDB

### Installation

#### Automated Installation (Linux/Raspberry Pi)

**For Raspberry Pi setup from scratch, see [README_RASPBERRY_PI.md](README_RASPBERRY_PI.md)**

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd <repository_directory>
   ```

2. Run the installation script:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

The script will:
- Install and configure Mosquitto MQTT broker
- Install and configure InfluxDB
- Install and configure Grafana
- Create Python virtual environment
- Install required Python packages
- Create systemd services for automatic startup
- Generate startup scripts

#### Manual Installation

1. Install system dependencies:
   ```bash
   sudo apt update
   sudo apt install -y mosquitto mosquitto-clients influxdb grafana
   ```

2. Install Python packages:
   ```bash
   pip install paho-mqtt influxdb pytz pyyaml pyserial
   ```

3. Configure services and copy equipment template:
   ```bash
   cp equipment_config.yml.template equipment_config.yml
   ```

### Running the System

#### Using Systemd Services (Recommended)

After installation, services are automatically started:

```bash
# Check service status
sudo systemctl status power_regulation
sudo systemctl status teleinfo

# Control services
sudo systemctl start/stop/restart power_regulation
sudo systemctl start/stop/restart teleinfo
```

#### Manual Execution

Execute scripts directly:

```bash
# Main regulation script
python power_regulation.py

# Teleinfo data collection
python teleinfo.py
```

#### Using Startup Scripts

```bash
# Start power regulation
./start_power_regulation.sh

# Start teleinfo
./start_teleinfo.sh
```

### Post-Installation Configuration

#### Security Setup

1. Configure MQTT authentication:
   ```bash
   sudo mosquitto_passwd -c /etc/mosquitto/passwd <username>
   ```

2. Edit MQTT configuration:
   ```bash
   sudo nano /etc/mosquitto/mosquitto.conf
   ```

3. Access Grafana dashboard:
   - URL: http://localhost:3000
   - Default login: admin/admin

#### Application Settings

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

4. Teleinfo Connection Issues:
   - Ensure serial port `/dev/ttyAMA0` is accessible
   - Check Linky meter TIC output connection
   - Verify serial port permissions

5. Service Issues:
   - Check service logs: `sudo journalctl -u power_regulation -f`
   - Check service logs: `sudo journalctl -u teleinfo -f`
   - Restart services: `sudo systemctl restart power_regulation teleinfo`

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
[Linky Meter] -> [teleinfo.py] -> [MQTT Broker] <-> [power_regulation.py] <-> [InfluxDB]
                                        ^                    |
                                        |                    v
                                 [Equipment Control]    [Equipment Classes]
```

## Infrastructure

This project primarily consists of Python scripts and does not have a dedicated infrastructure stack. However, it relies on the following external services:

- MQTT Broker: For real-time communication of power measurements and equipment control
- InfluxDB: Time-series database for storing power and energy data

Ensure these services are properly set up and configured in your environment.

## Teleinfo Module

The `teleinfo.py` module reads data from French Linky smart meters via the TIC (Télé-Information Client) interface.

### Features

- Reads teleinfo frames from serial port (`/dev/ttyAMA0`)
- Validates data integrity using checksums
- Publishes power measurements to MQTT topics:
  - `tic/SINSTI`: Injected power
  - `tic/SINSTS`: Consumed power  
  - `tic/ERQT`: Total reactive power
- Stores all measurements in InfluxDB

### Hardware Requirements

- Raspberry Pi or compatible device
- TIC interface connection to Linky meter
- Serial port access (`/dev/ttyAMA0`)

### Configuration

The teleinfo module uses the same configuration as the main system from `config.py`:

- MQTT broker settings
- InfluxDB connection parameters
- Logging configuration

### Running Teleinfo

```bash
python teleinfo.py
```

Logs are written to `/home/bruno/teleinfo-releve.log`.