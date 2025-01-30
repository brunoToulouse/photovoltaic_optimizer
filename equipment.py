import time
import math
from threading import Timer


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

# This module defines various equipments type depending on their control mechanism and power consumption profile.
# A brief summary of classes defined here:
# - Equipment: base class, with common behaviour and processing (including forcing and energy counter)
# - VariablePowerEquipment: an equipment which load can be controlled from 0 to 100%. It specifically uses the
#       digitally controlled SCR as described here: https://www.pierrox.net/wordpress/2019/03/04/optimisation-photovoltaique-3-controle-numerique-du-variateur-de-puissance/
# - UnknownPowerEquipment: an equipment which load can vary over time. It's controlled like a switch (either on or off).
#       This equipment is however not fully implemented as it has been specialized in the ConstantPowerEquipment below.
# - ConstantPowerEquipment: an equipment which load is fixed and known. It can be controlled like a switch.
#       ConstantPowerEquipment is essentially an optimization of UnknownPowerEquipment as it will allow the regulation
#       loop to match power consumption and production faster.

from debug import debug as debug

_mqtt_client = None
_send_commands = True


def setup(mqtt_client, send_commands):
    global _mqtt_client, _send_commands
    _mqtt_client = mqtt_client
    _send_commands = send_commands


def now_ts():
    return time.time()


class Equipment:
    def __init__(self,id, name):
        self.id = id
        self.name = name
        self.min_energy = None
        self.need_to_be_forced = False
        self.energy = 0
        self.current_power = 0
        self.last_power_change_date = None
        self.is_on = True
        self.is_ready = False
        self.previous_energy = None
        self.current_energy = None

    def decrease_power_by(self, watt):
        """ Return the amount of power that has been canceled, None if unknown """
        # implement in subclasses
        pass

    def increase_power_by(self, watt):
        """ Return the amount of power that is left to use, None if unknown """
        # implement in subclasses
        pass

    def set_current_power(self, power):
        if self.last_power_change_date is not None:
            now = now_ts()
            delta = now - self.last_power_change_date
            energy = self.current_power * delta / 3600.0
            self.__add_energy ( energy )
           
        self.current_power = power
        if power > 0 :
           self.is_on = True
        else:
           self.is_on = False
        self.last_power_change_date = now_ts()

    def switchOn(self):
        # implement in subclasses
        pass
    
    def switchOff(self):
        # implement in subclasses
        pass

    def setManualMode(self):
        # implement in subclasses
        pass

    def setAutoMode(self):
        # implement in subclasses
        pass

    def isAutoMode(self):
        return self.__mode_auto

    def isReady(self):
        # implement in subclasses
        pass
    
    def needToBeForced(self):
        # implement in subclasses
        pass
    
        
    def get_current_power(self):
        return self.current_power

    def get_energy(self):
        now = now_ts()
        delta = now - self.last_power_change_date
        current_energy = self.energy + ( self.current_power * delta / 3600.0 )
        return current_energy

    def __add_energy(self,energy):
        self.energy += energy
        

    def reset_energy(self):
        if self.last_power_change_date is not None:
            now = now_ts()
            delta = now - self.last_power_change_date
            energy = self.current_power * delta / 3600.0
            self.__add_energy(energy)
        self.previous_energy = self.current_energy
        self.current_energy = self.energy
        self.energy = 0
        self.last_power_change_date = now_ts()
        return self.previous_energy

class RepeatTimer(Timer):  
    def run(self):  
        while not self.finished.wait(self.interval):  
            self.function(*self.args,**self.kwargs)  
            debug(4,'*** retarting timer for next period : sleeping process for ' + str(self.interval) + ' seconds')

class VariablePowerEquipment(Equipment):
    MINIMUM_POWER = 50
    MINIMUM_PERCENT = 0

    def __init__(self,id,name, max_power,min_energy,period):
        Equipment.__init__(self,id, name)
        _mqtt_client.subscribe('scr/{0}/control'.format(self.id))
        self.max_power = max_power
        self.min_energy = min_energy
        self._mode_auto = True
        self.reset_energy()
        self.period = period
        self.timer = RepeatTimer(period, self.timer_call_back)
        self.timer.start()
    
    def timer_call_back(self):
       
        self.reset_energy()
        debug(4, "*** Checking current energy accumulated for " + self.name + " : " + str(self.current_energy))
        debug(4, "*** Checking previous energy accumulated for " + self.name + " : " + str(self.previous_energy))
        debug(4, "*** Checking minimum energy for " + self.name + " : " + str(self.min_energy))
        debug(4, "*** Needs to be forced "+ self.name + " : " + str(self.needToBeForced()))

    def isAutoMode(self):
        return self._mode_auto

    def setManualMode(self):
        self._mode_auto=False

    def setAutoMode(self):
        self._mode_auto=True
    
    def switchOn(self):
        if self._mode_auto==False:
           debug(1, "Manual mode ok : switching on equipment " + self.name +" to max power")
           self.set_current_power(self.max_power)
        else:
           debug(1, "Manual mode not set : switch on impossible for equipment " + self.name)

    
    def switchOff(self):
        if self._mode_auto==False:
           debug(1, "Manual mode ok : switching off equipment " + self.name)
           self.set_current_power(0)
        else:
           debug(1, "Manual mode not set : switch off impossible for equipment " + self.name)
    
    def isReady(self):
        if self.get_energy() >= self.min_energy:
           self.is_ready = True
           self.setAutoMode()
           self.set_current_power(0)
        else :
           self.is_ready = False
        return self.is_ready

    def needToBeForced(self):
        self.need_to_be_forced = False
        #debug(1,str(self.previous_energy) + " " + str(self.current_energy) +" "+ str(self.min_energy))
        if self.min_energy is not None and self.previous_energy is not None and self.current_energy is not None:
           if self.previous_energy < self.min_energy and self.current_energy < self.min_energy:

              self.need_to_be_forced = True
              if self.get_energy() > self.min_energy:
                 debug(4,'*** escaping forced mode for' + self.name + ': energy accumulated='+ str(self.get_energy()))
                 self.need_to_be_forced = False
                 self.set_current_power(0)
           else :
              self.need_to_be_forced = False
        return self.need_to_be_forced

    def set_current_power(self, power):
        if power > self.max_power:
           power = self.max_power
        super(VariablePowerEquipment, self).set_current_power(power)

        # regression factors computed from the response measurement of the SCR regulator
        a=1156.7360635374
        b=-2733.09296216279
        c=2365.91298447422
        d=-924.443712230202
        e=218.242717162968
        f=-0.010002294517421
        g=11.3205979917473

        z = self.current_power / float(self.max_power)
#            percent = g + f/z + e*z + d*z*z + c*z*z*z + b*z*z*z*z + a*z*z*z*z*z
        percent = math.acos(1-(2*z))/math.pi * 100

        if _send_commands:
            _mqtt_client.publish('scr/{0}/in'.format(self.id), str(percent))
        debug(4, "sending power command {}W ({}%) for {}".format(self.current_power, percent, self.name))


    def decrease_power_by(self, watt):
        if watt >= self.current_power:
            decrease = self.current_power
        else:
            decrease = watt

        if self.current_power - decrease < VariablePowerEquipment.MINIMUM_POWER:
            debug(4, "turning off power because it is below the minimum power: "+str(VariablePowerEquipment.MINIMUM_POWER))
            decrease = self.current_power

        if decrease > 0:
            old = self.current_power
            new = self.current_power - decrease
            self.set_current_power(new)
            debug(4, "decreasing power consumption of {} by {}W, from {} to {}".format(self.name, decrease, old, new))
        else:
            debug(4, "not decreasing power of {} because it is already at 0W".format(self.name))

        return decrease

    def increase_power_by(self, watt):
        if self.current_power + watt >= self.max_power:
            increase = self.max_power - self.current_power
            remaining = watt - increase
        else:
            increase = watt
            remaining = 0

        if self.current_power + increase < VariablePowerEquipment.MINIMUM_POWER:
            debug(4, "not increasing power because it doesn't reach the minimal power: "+str(VariablePowerEquipment.MINIMUM_POWER))
            increase = 0
            remaining = watt

        if increase == 0:
            debug(4, "status quo")
        elif increase > 0:
            old = self.current_power
            new = self.current_power + increase
            self.set_current_power(new)
            debug(4, "increasing power consumption of {} by {}W, from {} to {}".format(self.name, increase, old, new))
        else:
            debug(4, "not increasing power of {} because it is already at maximum power {}W".format(self.name, self.max_power))

        return remaining

class TempDrivenVariablePowerEquipment(Equipment):
    MINIMUM_POWER = 50
    MINIMUM_PERCENT = 0

    def __init__(self,id,name, max_power,temp_min,temp_eco,temp_sol_min,temp_max):
        Equipment.__init__(self,id, name)
        _mqtt_client.subscribe('scr/{0}/control'.format(self.id))
        _mqtt_client.subscribe('scr/{0}/temperature'.format(self.id))
        self.max_power = max_power
        self._temp_min = temp_min
        self._temp_sol_min = temp_sol_min
        self._temp_max = temp_max
        self._temp_eco = temp_eco
        self._current_temp = float(temp_max)
        self._mode_auto = True
        self._needToBeForced = False
        self.reset_energy()

    def isAutoMode(self):
        return self._mode_auto

    def setManualMode(self):
        self._mode_auto=False

    def setAutoMode(self):
        self._mode_auto=True

    def setCurrentTemp(self,temp):
        self._current_temp=temp
    
    def setMinTemp(self,temp):
        self._temp_min=temp

    def setMaxTemp(self,temp):
        self._temp_max=temp

    def setEcoTemp(self,temp):
        self._temp_eco=temp

    def isReady(self):
        if self._current_temp >= self._temp_max:
           debug(4, self.name +" temperature : " + str(self._current_temp) + " greater than max : " + str(self._temp_max))
           self.is_ready = True
           self.setAutoMode()
           if self.current_power > 0: 
              self.set_current_power(0)
        else:
           if self._current_temp >= self._temp_sol_min and self.is_ready == True:
              self.is_ready = True
           else: 
              self.is_ready = False
        return self.is_ready
        
    def needToBeForced(self):
        if self._current_temp <= self._temp_min and self._current_temp >0:
        #   debug(4, self.name +" temperature : " + str(self._current_temp) + " lower than min : " + str(self._temp_min))
           self._needToBeForced = True
        elif self._current_temp >= self._temp_eco:
        #   if self.current_power !=0 and self.isAutoMode():
        #      self.set_current_power(0)
           self._needToBeForced = False
        return self._needToBeForced
           
    def switchOn(self):
        if self._mode_auto==False:
           debug(1, "Manual mode ok : switching on equipment " + self.name +" to max power")
           self.set_current_power(self.max_power)
        else:
           debug(1, "Manual mode not set : switch on impossible for equipment " + self.name)

    
    def switchOff(self):
        if self._mode_auto==False:
           debug(1, "Manual mode ok : switching off equipment " + self.name)
           self.set_current_power(0)
        else:
           debug(1, "Manual mode not set : switch off impossible for equipment " + self.name)

    def set_current_power(self, power):
        if power > self.max_power:
           power = self.max_power
        Equipment.set_current_power(self,power)

        # regression factors computed from the response measurement of the SCR regulator
        a=1156.7360635374
        b=-2733.09296216279
        c=2365.91298447422
        d=-924.443712230202
        e=218.242717162968
        f=-0.010002294517421
        g=11.3205979917473

        z = self.current_power / float(self.max_power)
        #percent = g + f/z + e*z + d*z*z + c*z*z*z + b*z*z*z*z + a*z*z*z*z*z
        percent = math.acos(1-(2*z))/math.pi * 100

        if _send_commands:
            _mqtt_client.publish('scr/{0}/in'.format(self.id), str(percent))
        debug(4, "sending power command {}W ({}%) for {}".format(self.current_power, percent, self.name))


    def decrease_power_by(self, watt):
        if watt >= self.current_power:
            decrease = self.current_power
        else:
            decrease = watt

        if self.current_power - decrease < TempDrivenVariablePowerEquipment.MINIMUM_POWER:
            debug(4, "turning off power because it is below the minimum power: "+str(TempDrivenVariablePowerEquipment.MINIMUM_POWER))
            decrease = self.current_power

        if decrease > 0:
            old = self.current_power
            new = self.current_power - decrease
            self.set_current_power(new)
            debug(4, "decreasing power consumption of {} by {}W, from {} to {}".format(self.name, decrease, old, new))
        else:
            debug(4, "not decreasing power of {} because it is already at 0W".format(self.name))

        return decrease

    def increase_power_by(self, watt):
        if self.current_power + watt >= self.max_power:
            increase = self.max_power - self.current_power
            remaining = watt - increase
        else:
            increase = watt
            remaining = 0

        if self.current_power + increase < VariablePowerEquipment.MINIMUM_POWER:
            debug(4, "not increasing power because it doesn't reach the minimal power: "+str(VariablePowerEquipment.MINIMUM_POWER))
            increase = 0
            remaining = watt

        if increase == 0:
            debug(4, "status quo")
        elif increase > 0:
            old = self.current_power
            new = self.current_power + increase
            self.set_current_power(new)
            debug(4, "increasing power consumption of {} by {}W, from {} to {}".format(self.name, increase, old, new))
        else:
            debug(4, "not increasing power of {} because it is already at maximum power {}W".format(self.name, self.max_power))


class ConstantPowerEquipment(Equipment):
    def __init__(self, name, nominal_power):
        Equipment.__init__(self, name)
        self.nominal_power = nominal_power
        self.is_on = False

    def set_current_power(self, power):
        super(ConstantPowerEquipment, self).set_current_power(power)
        self.is_on = power != 0
        msg = '1' if self.is_on else '0'
        if _send_commands:
            _mqtt_client.publish('wifi_plug/0/in', msg, retain=True)
        debug(4, "sending power command {} for {}".format(self.is_on, self.name))

    def decrease_power_by(self, watt):
        if self.is_on:
            debug(4, "shutting down {} with a consumption of {}W to recover {}W".format(self.name, self.nominal_power, watt))
            self.set_current_power(0)
            return self.nominal_power
        else:
            debug(4, "{} with a power of {}W is already off".format(self.name, self.nominal_power))
            return 0

    def increase_power_by(self, watt):
        if self.is_on:
            debug(4, "{} with a power of {}W is already on".format(self.name, self.nominal_power))
            return watt
        else:
            if watt >= self.nominal_power:
                debug(4, "turning on {} with a consumption of {}W to use {}W".format(self.name, self.nominal_power, watt))
                self.set_current_power(self.nominal_power)
                return watt - self.nominal_power
            else:
                debug(4, "not turning on {} with a consumption of {}W because it would use more than the available {}W".format(self.name, self.nominal_power, watt))
                return watt


class UnknownPowerEquipment(Equipment):
    def __init__(self, name):
        Equipment.__init__(self, name)
        self.is_on = False

    def send_power_command(self):
        debug(4, "sending power command {} for {}".format(self.is_on, self.name))
        pass

    def decrease_power_by(self, watt):
        if self.is_on:
            self.is_on = False
            debug(4, "shutting down {} with an unknown consumption to recover {}W".format(self.name, watt))
            return None
        else:
            debug(4, "{} with an unknown power is already off".format(self.name))
            return 0

    def increase_power_by(self, watt):
        if self.is_on:
            debug(4, "{} with an unknown power is already on".format(self.name))
            return watt
        else:
            self.is_on = True
            debug(4, "turning on {} with an unknown consumption use {}W".format(self.name, watt))
            return None
