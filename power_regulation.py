#!/usr/bin/env python

# Copyright (C) 2018-2019 Pierre Hébert
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# WARNING: this software is exactly the one in use in the photovoltaic optimization project. It's tailored for my
#          own use and requires minor adaptations and configuration to run in other contexts.

# This is the main power regulation loop. It's purpose is to match the power consumption with the photovoltaic power.
# Using power measurements and a list of electrical equipments, with varying behaviors and control modes, the regulation
# loop takes decisions such as allocating more power to a given equipment when there is photovoltaic power in excess, or
# shutting down loads when the overall power consumption is higher than the current PV power supply.

# Beside the regulation loop, this software also handles these features
# - manual control ("force"), in order to be able to manually turn on/off a given equipment with a specified power and
#   duration.
# - monitoring: sends a JSON status message on a MQTT topic for reporting on the current regulation state
# - fallback: a very specific feature which aim is to make sure that the water heater receives enough water (either
#   from the PV panels or the grid to keep the water warm enough.

# See the "equipment module" for the definitions of the loads.


import json
import time
import pytz
import math
from datetime import datetime

from influxdb import InfluxDBClient
import paho.mqtt.client as mqtt

# Initialize InfluxDB client
from config import (INFLUXDB_HOST, INFLUXDB_PORT, INFLUXDB_USERNAME,
                   INFLUXDB_PASSWORD, INFLUXDB_DATABASE)

from debug import debug as debug
import equipment
from equipment import ConstantPowerEquipment, UnknownPowerEquipment, VariablePowerEquipment,TempDrivenVariablePowerEquipment

# The comparison between power consumption and production is done every N seconds, it must be above the measurement
# rate, which is currently 4s with the PZEM-004t module.
EVALUATION_PERIOD = 5

# Consider powers are balanced when the difference is below this value (watts). This helps prevent fluctuations.
BALANCE_THRESHOLD = 50

# Keep this margin (in watts) between the power production and consumption. This helps in reducing grid consumption
# knowing that there may be measurement inaccuracy.
MARGIN = 20

# A debug switch to toggle simulation (uses distinct MQTT topics for instance)
SIMULATION = False

last_evaluation_date = None

power_available = 0 
power_available_active = 0
power_consumed = 0
power_consumed_tot = 0
power_reactive = 0
previous_index_CR = 0
previous_ts_CR = None

mqtt_client = None

equipments = None
equipment_water_heater = None

# MQTT topics on which to subscribe and send messages
prefix = 's/' if SIMULATION else ''
TOPIC_INJECTED = prefix + "tic/SINSTI"
TOPIC_CONSUMED = prefix + "tic/SINSTS"
TOPIC_CONSUMED_REACTIVE = prefix + "tic/ERQT"
TOPIC_WATER_HEATER_TEMP = "scr/0/temperature"
TOPIC_STATUS = prefix + "regulation/status"

# connexion a la base de données InfluxDB
client = InfluxDBClient(host=INFLUXDB_HOST, port=INFLUXDB_PORT, username=INFLUXDB_USERNAME, password=INFLUXDB_PASSWORD, database=INFLUXDB_DATABASE)

connected = False
while not connected:
    try:
        print("Database %s exists?" % INFLUXDB_DATABASE)
        if not {'name': INFLUXDB_DATABASE} in client.get_list_database():
            print("Database %s creation.." % INFLUXDB_DATABASE)
            client.create_database(INFLUXDB_DATABASE)
            print("Database %s created!" % INFLUXDB_DATABASE)
        client.switch_database(INFLUXDB_DATABASE)
        print("Connected to %s!" % INFLUXDB_DATABASE)
    except Exception:
        print('InfluxDB is not reachable. Waiting 5 seconds to retry.')
        time.sleep(5)
    else:
        connected = True

def HC_ok():

    tz = pytz.timezone('Europe/Paris')
    now = datetime.now(tz)
    current_time = now.strftime("%H:%M")
    #if is_between(current_time, ("02:05", "16:50")):
    if is_between(current_time, ("02:05", "06:50")):
        #// or is_between(current_time, ("12:32","15:20")):
       return True
    else:
       return False

def is_between(time, time_range):
    if time_range[1] < time_range[0]:
        return time >= time_range[0] or time <= time_range[1]
    return time_range[0] <= time <= time_range[1]

def add_measures(key,val):
  try:
    points = []
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
  except Exception as e:
    debug(0, e)

def now_ts():
    # python2 support
    return time.time()


def get_equipment_by_id(id):
    for e in equipments:
        if e.id == int(id):
            return e
    return None

def set_instant_power(power):
    return power

def evaluate_power(previous_ts, previous_index,current_index,power):
    current_ts = now_ts()

    if previous_ts is not None:
       delta_ts = current_ts - previous_ts
       delta_index = current_index - previous_index
       if delta_index > 4: #on attend d'avoir au moins 5 W
          power = round(delta_index / delta_ts * 3600)
          previous_ts = current_ts
          previous_index = current_index
       elif delta_ts > 60 and delta_index > 1: # ou bien 2w en plus d'1 minute cad max 60wh
          power = round(delta_index / delta_ts * 3600)
          previous_ts = current_ts
          previous_index = current_index
       elif delta_ts > 120: # ou bien pls de 2 minutes on considere 0w
          power = 0.00
          previous_ts = current_ts
          previous_index = current_index
    else:
       previous_ts = current_ts
       previous_index = current_index
    return [previous_ts, previous_index,current_index,float(power)]


def on_connect(client, userdata, flags, rc):
    debug(0, 'ready')

    client.subscribe(TOPIC_INJECTED)
    client.subscribe(TOPIC_CONSUMED)
    client.subscribe(TOPIC_CONSUMED_REACTIVE)


def on_message(client, userdata, msg):
    # Receive power consumption and production values and triggers the evaluation. We also take into account manual
    # control messages in case we want to turn on/off a given equipment.
    global power_available,power_consumed_tot,power_reactive, previous_index_CR, previous_ts_CR
    if msg.topic == TOPIC_INJECTED:
        power_available=set_instant_power(int(msg.payload.decode()))
        add_measures("power_available",power_available)
    elif "/temperature" in msg.topic:
        id_equipment=msg.topic.split("/")[1]
        e = get_equipment_by_id(id_equipment)
        temp=float(msg.payload.decode())
        add_measures(e.name + "-temp",temp)
        e.setCurrentTemp(temp)
    elif "/control" in msg.topic:
        id_equipment=msg.topic.split("/")[1]
        e = get_equipment_by_id(id_equipment)
        wh_command=str(msg.payload.decode())
        if wh_command=="ON":
           e.setManualMode()
           e.switchOn()
        elif wh_command=="OFF":
           e.setManualMode()
           e.switchOff()
        elif wh_command=="AUTO":
           e.setAutoMode()
        elif "MIN" in wh_command:
           temp=wh_command.split(";")[1]
           e.setMinTemp(float(temp))
        elif "MAX" in wh_command:
           temp=wh_command.split(";")[1]
           e.setMaxTemp(float(temp))
        elif "ECO" in wh_command:
           temp=wh_command.split(";")[1]
           e.setEcoTemp(float(temp))
    elif msg.topic == TOPIC_CONSUMED_REACTIVE:
        [previous_ts_CR,previous_index_CR,current_index_CR,power_reactive]=evaluate_power(previous_ts_CR,previous_index_CR,int(msg.payload.decode()),power_reactive)
        add_measures("power_reactive",power_reactive)
    elif msg.topic == TOPIC_CONSUMED:
        power_consumed_tot=set_instant_power(int(msg.payload.decode()))
        add_measures("power_consumed_tot",power_consumed_tot)
    evaluate()


# Specific fallback: the energy put in the water heater yesterday (see below)
energy_yesterday = 0

def evaluate():
    # This is where all the magic happen. This function takes decision according to the current power measurements.
    # It examines the list of equipments by priority order, their current state and computes which one should be
    # turned on/off.

    global last_evaluation_date
    
    t=now_ts()
    if last_evaluation_date is not None:
       # ensure there's a minimum duration between two evaluations
       if t - last_evaluation_date < EVALUATION_PERIOD:
          return

    last_evaluation_date = t

#    power_consumed=power_consumed_HP + power_consumed_HC
    power_consumed=power_consumed_tot - power_available
    power_available_active=-1* power_consumed
    if power_available_active >0:
       power_available_active = math.sqrt(abs(power_available_active**2 - power_reactive**2))
       power_consumed=float(0)
    else:
       power_available_active=float(0)
       power_consumed = math.sqrt(abs(power_consumed**2 - power_reactive**2))
       
    add_measures("power_available_active",power_available_active)
    add_measures("power_consumed",power_consumed)
    try:
        if HC_ok():
          debug(0, "HEURES CREUSES : checking equipment to be forced")
          for i, e in enumerate(equipments):
            if not e.isAutoMode():
               debug(1, "skipping this equipment because it's in manual mode")
               continue
          
            if e.needToBeForced():
               if e.get_current_power() != e.max_power:
               
                  debug(1, "Switching on equipment " + e.name + " because it is to be forced and power is " + str(e.get_current_power()))
                  e.set_current_power(e.max_power)
               else:
                  debug(1, "equipment " + e.name + " is already forced")

        debug(0, '')
        debug(0, 'evaluating power consumption={}, power production={}'.format(power_consumed, power_available))

 
       # Here starts the real work, compare powers
        if power_available_active <= 0 and power_consumed > BALANCE_THRESHOLD:
            # Too much power consumption, we need to decrease the load
            excess_power = power_consumed / 4
            debug(0, "decreasing global power consumption by {}W".format(excess_power))
            for e in reversed(equipments):
                debug(2, "examining " + e.name)
                if e.needToBeForced() and HC_ok():
                    debug(4, "skipping this equipment because it's in forced state")
                    continue
                if not e.isAutoMode():
                    debug(4, "skipping this equipment because it's in manual mode")
                    continue
                result = e.decrease_power_by(excess_power)
                if result is None:
                    debug(2, "stopping here and waiting for the next measurement to see the effect")
                    break
                excess_power -= result
                if excess_power <= 0:
                    debug(2, "no more excess power consumption, stopping here")
                    break
                else:
                    debug(2, "there is {}W left to cancel, continuing".format(excess_power))
            debug(2, "no more equipment to check")
        elif power_available_active >0 and power_available_active <= BALANCE_THRESHOLD:
            # Nice, this is the goal: consumption is equal to production
            debug(0, "power consumption and production are balanced")
        elif power_available_active > 0:
            # There's power in excess, try to increase the load to consume this available power
            available_power = power_available_active/4
            debug(0, "increasing global power consumption by {}W".format(available_power))
            for i, e in enumerate(equipments):
                if available_power <= 0:
                    debug(2, "no more available power")
                    break
                debug(2, "examining " + e.name)
                if e.needToBeForced() and HC_ok():
                    debug(4, "skipping this equipment because it's in force state")
                    continue
                if e.isReady():
                    debug(4, "skipping this equipment because it's in ready state")
                    continue
                if not e.isAutoMode():
                    debug(4, "skipping this equipment because it's in manual mode")
                    continue
                #debug(4," ***** " + str(e.needToBeForced()) + " **** " + str(HC_ok()))
                result = e.increase_power_by(available_power)
                if result is None:
                    debug(2, "stopping here and waiting for the next measurement to see the effect")
                    break
                elif result == 0:
                    debug(2, "no more available power to use, stopping here")
                    break
                elif result < 0:
                    debug(2, "not enough available power to turn on this equipment, trying to recover power on lower priority equipments")
                    freeable_power = 0
                    needed_power = -result
                    for j in range(i + 1, len(equipments)):
                        o = equipments[j]
                        if o.needToBeForced() and HC_ok():
                            continue
                        p = o.get_current_power()
                        if p is not None:
                            freeable_power += p
                    debug(2, "power used by other equipments: {}W, needed: {}W".format(freeable_power, needed_power))
                    if freeable_power >= needed_power:
                        debug(2, "recovering power")
                        freed_power = 0
                        for j in reversed(range(i + 1, len(equipments))):
                            o = equipments[j]
                            if o.needToBeForced() and HC_ok():
                                continue
                            result = o.decrease_power_by(needed_power)
                            freed_power += result
                            needed_power -= result
                            if needed_power <= 0:
                                debug(2, "enough power has been recovered, stopping here")
                                break
                        new_available_power = available_power + freed_power
                        debug(2, "now trying again to increase power of {} with {}W".format(e.name, new_available_power))
                        available_power = e.increase_power_by(new_available_power)
                    else:
                        debug(2, "this is not possible to recover enough power on lower priority equipments")
                else:
                    available_power = result
                    debug(2, "there is {}W left to use, continuing".format(available_power))
            debug(2, "no more equipment to check")

        # Build a status message
        status = {
            'date': t,
            'date_str': datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S'),
            'power_available': power_available,
            'power_consumed': power_consumed,
        }
        es = []
        for e in equipments:
            p = e.get_current_power()
            es.append({
                'name': e.name,
                'current_power': 'unknown' if p is None else p,
                'energy': e.get_energy(),
                'forced': e.needToBeForced()
            })
            add_measures("{}-power".format(e.name),round(p))
            add_measures("{}-energy".format(e.name),round(e.get_energy()))
            add_measures("{}-is_forced".format(e.name),e.needToBeForced())
            
        status['equipments'] = es
        mqtt_client.publish(TOPIC_STATUS, json.dumps(status))

    except Exception as e:
        debug(2, e)


def main():
    global mqtt_client, equipments, equipment_water_heater

    mqtt_client = mqtt.Client()
    from config import (MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE,
                      MQTT_USERNAME, MQTT_PASSWORD)
    
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE)

    equipment.setup(mqtt_client, not SIMULATION)

    # Load equipment configurations from YAML file
    from equipment_loader import load_equipment_from_config
    equipments = tuple(load_equipment_from_config())

    # At startup, reset everything
    for e in equipments:
        e.set_current_power(0)

    mqtt_client.loop_forever()


if __name__ == '__main__':
    main()
