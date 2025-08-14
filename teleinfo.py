#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ = "Sébastien Reuiller"
# __licence__ = "Apache License 2.0"

# Python 3, prérequis : pip install pySerial influxdb
#
# Exemple de trame:
# {
#  'BASE': '123456789'       # Index heure de base en Wh
#  'OPTARIF': 'HC..',        # Option tarifaire HC/BASE
#  'IMAX': '007',            # Intensité max
#  'HCHC': '040177099',      # Index heure creuse en Wh
#  'IINST': '005',           # Intensité instantanée en A
#  'PAPP': '01289',          # Puissance Apparente, en VA
#  'MOTDETAT': '000000',     # Mot d'état du compteur
#  'HHPHC': 'A',             # Horaire Heures Pleines Heures Creuses
#  'ISOUSC': '45',           # Intensité souscrite en A
#  'ADCO': '000000000000',   # Adresse du compteur
#  'HCHP': '035972694',      # index heure pleine en Wh
#  'PTEC': 'HP..'            # Période tarifaire en cours
# }

import paho.mqtt.client as mqtt
import logging
import time
from datetime import datetime
import serial
from influxdb import InfluxDBClient
import config
import os


def on_connect(client, userdata, flags, rc):
    if rc==0:
        print("connected OK Returned code=",rc)
    else:
        print("Bad connection Returned code=",rc)


# clés téléinfo
INT_MESURE_KEYS = ['BASE', 'IMAX', 'HCHC', 'IINST', 'PAPP', 'ISOUSC', 'ADCO', 'HCHP']

# création du logguer
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'teleinfo-releve.log')
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s %(message)s')
logging.info("Teleinfo starting..")

# connexion a la base de données InfluxDB
client = InfluxDBClient(config.INFLUXDB_HOST, config.INFLUXDB_PORT, 
                       config.INFLUXDB_USERNAME, config.INFLUXDB_PASSWORD)
DB_NAME = config.INFLUXDB_DATABASE
connected = False
while not connected:
    try:
        logging.info("Database %s exists?", DB_NAME)
        if {'name': DB_NAME} not in client.get_list_database():
            logging.info("Database %s creation..", DB_NAME)
            client.create_database(DB_NAME)
            logging.info("Database %s created!", DB_NAME)

        client.switch_database(DB_NAME)
        
        # Set retention policy to 1 year
        try:
            client.create_retention_policy('one_year', '365d', 1, database=DB_NAME, default=True)
            logging.info("Retention policy set to 1 year")
        except Exception as e:
            logging.info("Retention policy already exists or error: %s", e)
        
        logging.info("Connected to %s!", DB_NAME)
        connected = True 

    except Exception:
        logging.error("InfluxDB is not reachable. Waiting 5 seconds to retry...", exc_info=True)
        time.sleep(5)

#connection au broker mqtt
try:
  mqtt_client=mqtt.Client()
  mqtt_client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
  mqtt_client.on_connect = on_connect
  mqtt_client.connect(config.MQTT_BROKER_HOST, config.MQTT_BROKER_PORT, config.MQTT_KEEPALIVE)
except:
  logging.info('PB connecting to MQTT Server.')


def add_measures(key,val, time_measure):
    points = []
    if str(val).isnumeric():
       try:
        val = int(val)
       except:
        val = float(val)
       if key in ("EASF01","EASF02","EAIT","SINSTI","SINSTS","EAST","ERQT"):
          mqtt_client.publish("tic/{}".format(key),val)
    if key != "ADCO":
        point = {
            "measurement": key,
            "tags": {
                # identification de la sonde et du compteur
                "host": "raspberry",
                "region": "linky"
            },
            "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fields": {
                "value": val
            }
        }
        #print(point)
        points.append(point)
        client.write_points(points)

def verif_checksum(data, checksum):
    data_unicode = 0
    for caractere in data:
        data_unicode += ord(caractere)
    sum_unicode = (data_unicode & 63) +  32
    verif = chr(sum_unicode)
    logging.debug("{} - {} - {}".format(data,ord(checksum),sum_unicode))
    return (checksum == chr(sum_unicode))


def main():
   with serial.Serial(port='/dev/ttyAMA0', baudrate=9600, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE,
                       bytesize=serial.SEVENBITS, timeout=1) as ser:
      try:
        logging.info("Teleinfo is reading on /dev/ttyS0..")
        # boucle pour partir sur un début de trame
        line = ser.readline()
        while b'\x02' not in line:  # recherche du caractère de début de trame
            line = ser.readline()

        # lecture de la première ligne de la première trame
        line = ser.readline()

        while True:
            key = val = "<undef>"  # valeurs par défaut pour éviter crash dans except

            line_str = line.decode("utf-8")
            logging.debug(line)
            # separation sur espace /!\ attention le caractere de controle 0x32 est un espace aussi
            logging.debug(line_str)
            arr=line_str.split("\t")
            if len(arr) < 2:
               raise ValueError(f"Trame incomplète: {line_str!r}")
            rest_ind=len(arr)-1
            key=arr[0]
            rest=arr[rest_ind]
            val=line_str[0:len(line_str)-len(rest)-1][len(key)+1:]
            #[key, val, rest] = line_str.split("\t")
            # supprimer les retours charriot et saut de ligne puis selectionne le caractere
            # de controle en partant de la fin
            checksum = (rest.replace('\x03\x02', '')).replace("\r\n","")
            #checksum = rest
            if verif_checksum(f"{key}\t{val}\t", checksum):
            # creation du champ pour la trame en cours avec cast des valeurs de mesure en "integer"
 
               time_measure = time.time()
               # insertion dans influxdb
               add_measures(key, val, time_measure)
               if key=="ERQ1":
                   print("ERQ1:"+val)
                   ERQ1val=int(val)
               if key=="ERQ2":
                   ERQ2val=int(val)
               if key=="ERQ3":
                   ERQ3val=int(val)
               if key=="ERQ4":
                   ERQ4val=int(val)
               if "ERQ" in key:
                   ERQ=ERQ1val+ERQ2val+ERQ3val+ERQ4val
                   add_measures("ERQT", ERQ, time_measure)

            else:
               logging.info("checksum invalid {} : {}".format(key,val))

      except Exception as e:
            logging.error("Exception : %s" % e, exc_info=True)
            logging.error("%s %s" % (key, val))
            line = ser.readline()
 

if __name__ == '__main__':
    if connected:
       print('entering main program')
       while True:
         try:
           main()
         except Exception as e:
           logging.error("Exception : %s" % e)
           time.sleep(15)

