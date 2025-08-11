#!/bin/bash

set -e
echo "installation de mosquitto"
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
# Activer et démarrer le service Mosquitto
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

echo " TODO mettre le mdp à l'aide de mosquitto_passwd et modifier la conf /etc/mosquitto/mosquitto.conf"

echo "installation de influxdb"
# Importer la clé officielle et ajouter le repo

curl https://repos.influxdata.com/influxdata-archive.key | gpg --dearmor | sudo tee /usr/share/keyrings/influxdb-archive-keyring.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/influxdb-archive-keyring.gpg] https://repos.influxdata.com/debian stable main" | sudo tee /etc/apt/sources.list.d/influxdb.list

sudo apt update
sudo apt install influxdb

# Activer et démarrer influxdb
sudo systemctl enable influxdb
sudo systemctl start influxdb

echo "installation de grafana"
sudo apt install -y apt-transport-https software-properties-common wget

wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -

sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"

sudo apt update
sudo apt install grafana

# Activer et démarrer grafana-server
sudo systemctl enable grafana-server
sudo systemctl start grafana-server


# 1. Dossier où se trouve ce script et le projet
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export HOME_PHOTOVOLTAIC_OPTIMIZER="$SCRIPT_DIR"

# 2. Ajouter la variable dans ~/.bashrc si absente
if ! grep -q "HOME_PHOTOVOLTAIC_OPTIMIZER" "$HOME/.bashrc"; then
    {
        echo ""
        echo "# Chemin du projet Photovoltaic Optimizer"
        echo "export HOME_PHOTOVOLTAIC_OPTIMIZER=\"$SCRIPT_DIR\""
    } >> "$HOME/.bashrc"
fi

# 3. Créer l'environnement virtuel si absent
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    python3 -m venv "$SCRIPT_DIR/venv"
fi

# 4. Installer les paquets Python dans le venv
source "$SCRIPT_DIR/venv/bin/activate"
pip install --upgrade pip
pip install paho-mqtt influxdb pytz pyyaml pySerial
deactivate

# 5. Créer le start.sh wrapper
cat > "$SCRIPT_DIR/start_power_regulation.sh" << 'EOF'
#!/bin/bash
source ~/.bashrc
source "$HOME_PHOTOVOLTAIC_OPTIMIZER/venv/bin/activate"
exec python "$HOME_PHOTOVOLTAIC_OPTIMIZER/power_regulation.py"
EOF

cat > "$SCRIPT_DIR/start_teleinfo.sh" << 'EOF'
#!/bin/bash
source ~/.bashrc
source "$HOME_PHOTOVOLTAIC_OPTIMIZER/venv/bin/activate"
exec python "$HOME_PHOTOVOLTAIC_OPTIMIZER/teleinfo.py"
EOF

chmod +x "$SCRIPT_DIR/start_teleinfo.sh"

# 6. Générer les fichiers systemd .service
SERVICE_NAME1="power_regulation.service"
SERVICE_PATH1="/etc/systemd/system/$SERVICE_NAME1"

sudo bash -c "cat > $SERVICE_PATH1" <<EOF
[Unit]
Description=Power regulation Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
Environment=HOME_PHOTOVOLTAIC_OPTIMIZER=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/start_power_regulation.sh
Restart=always

[Install]
WantedBy=multi-user.target
EOF

SERVICE_NAME2="teleinfo.service"
SERVICE_PATH2="/etc/systemd/system/$SERVICE_NAME2"

sudo bash -c "cat > $SERVICE_PATH2" <<EOF
[Unit]
Description=Teleinfo Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
Environment=HOME_PHOTOVOLTAIC_OPTIMIZER=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/start_teleinfo.sh
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 7. Recharger systemd, activer et démarrer le service
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME1
sudo systemctl start $SERVICE_NAME1
sudo systemctl enable $SERVICE_NAME2
sudo systemctl start $SERVICE_NAME2


# Copy equipment config template if config doesn't exist
if [ ! -f equipment_config.yml ]; then
    cp equipment_config.yml.template equipment_config.yml
    echo "Created equipment_config.yml from template"
fi


echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Configure MQTT and InfluxDB settings in config.py"
echo "2. Set up your equipment in equipment_config.yml"
echo "3. Restart services"
