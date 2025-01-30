"""Configuration parameters for MQTT connection, InfluxDB and other settings.

Configuration can be overridden using environment variables:
- MQTT_BROKER_HOST: Main broker hostname/IP
- MQTT_BROKER_PORT: Main broker port
- MQTT_KEEPALIVE: Connection keepalive time in seconds
- MQTT_USERNAME: Authentication username
- MQTT_PASSWORD: Authentication password

- INFLUXDB_HOST: InfluxDB server hostname/IP
- INFLUXDB_PORT: InfluxDB server port
- INFLUXDB_DATABASE: InfluxDB database name
- INFLUXDB_USERNAME: InfluxDB authentication username 
- INFLUXDB_PASSWORD: InfluxDB authentication password
"""

import os

# MQTT Connection Settings
MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'localhost')
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))
MQTT_KEEPALIVE = int(os.getenv('MQTT_KEEPALIVE', '120'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', 'bruno')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', 'bruno')

# InfluxDB Connection Settings
INFLUXDB_HOST = os.getenv('INFLUXDB_HOST', 'localhost')
INFLUXDB_PORT = int(os.getenv('INFLUXDB_PORT', '8086'))
INFLUXDB_DATABASE = os.getenv('INFLUXDB_DATABASE', 'teleinfo')
INFLUXDB_USERNAME = os.getenv('INFLUXDB_USERNAME', '')
INFLUXDB_PASSWORD = os.getenv('INFLUXDB_PASSWORD', '')
