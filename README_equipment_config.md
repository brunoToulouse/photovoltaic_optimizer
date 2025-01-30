# Equipment Configuration Guide

## Overview
Equipment configurations can now be managed through the `equipment_config.yml` file instead of hardcoding them in the source code. This makes it easier to modify equipment settings without changing the code.

## Configuration File Structure
The configuration file (`equipment_config.yml`) uses YAML format and supports the following equipment types:

1. VariablePowerEquipment
2. TempDrivenVariablePowerEquipment
3. ConstantPowerEquipment
4. UnknownPowerEquipment

## Example Configuration
```yaml
equipment:
  - type: VariablePowerEquipment
    id: "equipment1"
    name: "Water Heater"
    max_power: 2000
    min_energy: 2000
    period: 3600

  - type: TempDrivenVariablePowerEquipment
    id: "equipment2"
    name: "Heat Pump"
    max_power: 3000
    temp_min: 19
    temp_eco: 20
    temp_sol_min: 21
    temp_max: 23
```

## Required Parameters by Equipment Type

### VariablePowerEquipment
- id: Unique identifier
- name: Equipment name
- max_power: Maximum power in watts
- min_energy: Minimum energy in watt-hours
- period: Period in seconds

### TempDrivenVariablePowerEquipment
- id: Unique identifier
- name: Equipment name
- max_power: Maximum power in watts
- temp_min: Minimum temperature
- temp_eco: Economy temperature
- temp_sol_min: Minimum solar temperature
- temp_max: Maximum temperature

### ConstantPowerEquipment
- name: Equipment name
- nominal_power: Power consumption in watts

### UnknownPowerEquipment
- name: Equipment name

## Notes
- Equipment are processed in the order they appear in the configuration file
- The first equipment in the list is treated as the water heater for legacy compatibility
- All power values are in watts
- All temperature values are in degrees Celsius
- All time values are in seconds