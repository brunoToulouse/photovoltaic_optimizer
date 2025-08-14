# Raspberry Pi Setup Guide

This guide covers the complete setup of a Raspberry Pi for the Photovoltaic Optimizer project.

## 1. Flash Raspberry Pi OS

### Using Raspberry Pi Imager (Recommended)

1. Download [Raspberry Pi Imager](https://www.raspberrypi.org/software/)
2. Insert SD card (minimum 16GB recommended)
3. Launch Raspberry Pi Imager
4. Click gear icon for advanced options:
   - Enable SSH with password authentication
   - Set username: `pi` and password
   - Configure WiFi (SSID and password)
   - Set locale settings
5. Select "Raspberry Pi OS Lite" (64-bit recommended)
6. Flash to SD card

### Manual Configuration (Alternative)

If not configured during flashing:

1. Enable SSH by creating empty file `ssh` in boot partition
2. Configure WiFi by creating `wpa_supplicant.conf` in boot partition:
   ```
   country=FR
   ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
   update_config=1
   
   network={
       ssid="YOUR_WIFI_NAME"
       psk="YOUR_WIFI_PASSWORD"
   }
   ```

## 2. Initial Boot and SSH Connection

1. Insert SD card and power on Raspberry Pi
2. Find Pi IP address:
   ```bash
   # From router admin panel or network scanner
   nmap -sn 192.168.1.0/24
   ```
3. Connect via SSH:
   ```bash
   ssh pi@<raspberry_pi_ip>
   ```

## 3. System Configuration

### Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### Configure Raspberry Pi
```bash
sudo raspi-config
```

Navigate using arrow keys, Enter to select, Tab to move between buttons:

1. **Interface Options** (select and press Enter)
   - **SSH**: Select → Enable → Yes → OK
   - **Serial Port**: Select → Enter
     - "Login shell over serial?": **No**
     - "Serial port hardware enabled?": **Yes**

2. **Advanced Options**
   - **Expand Filesystem**: Select → Yes

3. **Localisation Options**
   - **Timezone**: Select your timezone
   - **Locale**: Select your locale
   - **Keyboard**: Select keyboard layout

Reboot after configuration:
```bash
sudo reboot
```

## 4. Serial Port Configuration

### Disable Bluetooth (for UART access)
```bash
sudo nano /boot/config.txt
```

Add at the end:
```
# Disable Bluetooth to free up UART
dtoverlay=disable-bt
```

### Disable Serial Console
```bash
sudo systemctl disable hciuart
sudo nano /boot/cmdline.txt
```

Remove `console=serial0,115200` from the line (keep everything else).

### Verify Serial Port
```bash
ls -la /dev/tty*
# Should show /dev/ttyAMA0 or /dev/ttyS0
```

## 5. Install Prerequisites

### Install Essential Packages
```bash
sudo apt install -y git python3 python3-pip python3-venv curl wget
```

### Verify Python Installation
```bash
python3 --version
pip3 --version
```

## 6. Install Git and Clone Repository

### Clone Repository
```bash
cd ~
git clone https://github.com/your-username/photovoltaic_optimizer.git
cd photovoltaic_optimizer
```

## 7. Run Installation Script

```bash
chmod +x install.sh
./install.sh
```

The script will automatically:
- Install Mosquitto MQTT broker
- Install InfluxDB
- Install Grafana
- Create Python virtual environment
- Install Python dependencies
- Create systemd services
- Generate startup scripts

## 8. Hardware Connection

### Linky TIC Connection
Connect TIC interface to Raspberry Pi:
- TIC I1/I2 pins to GPIO 14/15 (UART)
- Ground connection
- 3.3V power if needed

### Verify Connection
```bash
# Test serial communication
sudo cat /dev/ttyAMA0
# Should show teleinfo data if connected properly
```

## 9. Post-Installation Configuration

### Configure MQTT Security
```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd bruno
sudo nano /etc/mosquitto/mosquitto.conf
```

Add:
```
allow_anonymous false
password_file /etc/mosquitto/passwd
```

Restart MQTT:
```bash
sudo systemctl restart mosquitto
```

### Restart All Services
```bash
sudo systemctl restart power_regulation teleinfo
```

### Configure Application

1. **Equipment Configuration**: See [README_equipment_config.md](README_equipment_config.md) for equipment setup
2. **System Configuration**: See main [README.md](README.md) for config.py settings

### Access Services
- **Grafana**: http://raspberry_pi_ip:3000 (admin/admin)
- **InfluxDB**: http://raspberry_pi_ip:8086

### Check Services Status
```bash
sudo systemctl status power_regulation
sudo systemctl status teleinfo
sudo systemctl status mosquitto
sudo systemctl status influxdb
sudo systemctl status grafana-server
```

## 10. Troubleshooting

### Serial Port Issues
```bash
# Check permissions
sudo usermod -a -G dialout pi
sudo chmod 666 /dev/ttyAMA0

# Test with different baud rates
stty -F /dev/ttyAMA0 9600
```

### Service Logs
```bash
# View service logs
sudo journalctl -u power_regulation -f
sudo journalctl -u teleinfo -f
```

### Network Issues
```bash
# Check network connectivity
ping google.com
ip addr show
```

## 11. Optional: Remote Access

### VNC (GUI Access)
```bash
sudo raspi-config
# Interface Options > VNC > Enable
```

### Port Forwarding
Configure router to forward ports:
- SSH: 22
- Grafana: 3000
- MQTT: 1883

## Security Notes

- Change default passwords
- Use SSH keys instead of passwords
- Configure firewall if needed
- Regular system updates