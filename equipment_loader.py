import yaml
from equipment import (
    VariablePowerEquipment,
    TempDrivenVariablePowerEquipment,
    ConstantPowerEquipment,
    UnknownPowerEquipment
)

def load_equipment_from_config(config_file='equipment_config.yml'):
    """Load equipment configurations from YAML file."""
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)

    equipment_list = []
    i=0
    for equip in config['equipment']:
        equipment_type = equip['type']
        equipment_id=i
        i=i+1
               
        if equipment_type == 'VariablePowerEquipment':
            equipment = VariablePowerEquipment(
                id=equipment_id,
                name=equip['name'],
                max_power=equip['max_power'],
                min_energy=equip['min_energy'],
                period=equip['period']
            )
        elif equipment_type == 'TempDrivenVariablePowerEquipment':
            equipment = TempDrivenVariablePowerEquipment(
                id=equipment_id,
                name=equip['name'],
                max_power=equip['max_power'],
                temp_min=equip['temp_min'],
                temp_eco=equip['temp_eco'],
                temp_sol_min=equip['temp_sol_min'],
                temp_max=equip['temp_max']
            )
        elif equipment_type == 'ConstantPowerEquipment':
            equipment = ConstantPowerEquipment(
                name=equip['name'],
                nominal_power=equip['nominal_power']
            )
        elif equipment_type == 'UnknownPowerEquipment':
            equipment = UnknownPowerEquipment(
                name=equip['name']
            )
        else:
            raise ValueError(f"Unknown equipment type: {equipment_type}")
            
        equipment_list.append(equipment)
    
    return equipment_list