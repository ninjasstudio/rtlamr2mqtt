"""
Helper functions for monitor mode
"""

import os
from yaml import safe_load, safe_dump


def guess_meter_type(protocol, consumption_rate=None):
    """
    Guess the meter type (gas or water) based on protocol and consumption patterns.
    
    Args:
        protocol (str): The meter protocol
        consumption_rate (int): Optional consumption value to help guess
    
    Returns:
        str: 'gas', 'water', or 'energy'
    """
    protocol = str(protocol).lower() if protocol else ''
    
    # SCM and SCM+ are typically water or gas
    # IDM and NetIDM are typically electric
    # R900 and R900BCD can be water or gas
    
    if protocol in ['idm', 'netidm']:
        return 'energy'
    elif protocol in ['scm', 'scm+']:
        # SCM is usually water, but can be gas
        # If consumption is very high, likely water (in gallons)
        # If consumption is lower, likely gas (in cubic feet)
        if consumption_rate and consumption_rate > 100000:
            return 'water'
        else:
            return 'gas'
    elif protocol in ['r900', 'r900bcd']:
        # R900 can be either water or gas
        # Higher consumption values typically indicate water meters
        if consumption_rate and consumption_rate > 50000:
            return 'water'
        else:
            return 'gas'
    
    return 'energy'  # Default to energy if unknown


def get_smart_defaults(meter_id, protocol, device_class):
    """
    Get smart defaults for a meter based on its type.
    
    Args:
        meter_id (str): The meter ID
        protocol (str): The meter protocol
        device_class (str): The device class (gas, water, energy)
    
    Returns:
        dict: Default configuration for the meter
    """
    defaults = {
        'id': int(meter_id),
        'protocol': protocol.lower(),
        'name': f'meter_{meter_id}',
        'device_class': device_class,
        'state_class': 'total_increasing'
    }
    
    # Add format and unit based on device class
    if device_class == 'water':
        defaults['format'] = '######.##'
        defaults['unit_of_measurement'] = 'gal'
    elif device_class == 'gas':
        defaults['format'] = '######.##'
        defaults['unit_of_measurement'] = 'ft³'
    elif device_class == 'energy':
        defaults['format'] = '######.###'
        defaults['unit_of_measurement'] = 'kWh'
    
    return defaults


class MonitorModeTracker:
    """
    Track discovered meters in monitor mode and save them to config.
    """
    
    def __init__(self, config_path, max_meters=25, logger=None):
        """
        Initialize the monitor mode tracker.
        
        Args:
            config_path (str): Path to the config file
            max_meters (int): Maximum number of meters to track
            logger: Logger instance
        """
        self.config_path = config_path
        self.max_meters = max_meters
        self.logger = logger
        self.discovered_meters = {}
        self.load_discovered_meters()
    
    def load_discovered_meters(self):
        """
        Load previously discovered meters from a separate file.
        """
        discovered_file = self.config_path.replace('.yaml', '_discovered.yaml').replace('.yml', '_discovered.yaml')
        if os.path.isfile(discovered_file) and os.access(discovered_file, os.R_OK):
            try:
                with open(discovered_file, 'r', encoding='utf-8') as f:
                    data = safe_load(f)
                    if data and 'discovered_meters' in data:
                        self.discovered_meters = data['discovered_meters']
                        if self.logger:
                            self.logger.info('Loaded %d previously discovered meters', len(self.discovered_meters))
            except Exception as e:
                if self.logger:
                    self.logger.warning('Failed to load discovered meters: %s', e)
    
    def add_meter(self, meter_id, protocol, consumption=None):
        """
        Add a discovered meter to the tracking list.
        
        Args:
            meter_id (str): The meter ID
            protocol (str): The meter protocol
            consumption (int): Optional consumption value
        """

        # Ensure protocol is a string
        protocol = str(protocol) if protocol else ''
        
        if meter_id not in self.discovered_meters:
            if len(self.discovered_meters) < self.max_meters:
                device_class = guess_meter_type(protocol, consumption)
                self.discovered_meters[meter_id] = {
                    'protocol': protocol.lower(),
                    'device_class': device_class,
                    'first_seen_consumption': consumption
                }
                if self.logger:
                    self.logger.info('Discovered new meter: ID=%s, Protocol=%s, Type=%s', 
                                     meter_id, protocol, device_class)
    
    def save_discovered_meters(self):
        """
        Save discovered meters to a separate file.
        """
        discovered_file = self.config_path.replace('.yaml', '_discovered.yaml').replace('.yml', '_discovered.yaml')
        try:
            data = {'discovered_meters': self.discovered_meters}
            with open(discovered_file, 'w', encoding='utf-8') as f:
                safe_dump(data, f, default_flow_style=False, allow_unicode=True)
            if self.logger:
                self.logger.info('Saved %d discovered meters to %s', len(self.discovered_meters), discovered_file)
        except Exception as e:
            if self.logger:
                self.logger.error('Failed to save discovered meters: %s', e)
    
    def update_config_with_discovered_meters(self):
        """
        Update the main config file with discovered meters.
        This should be called on shutdown or periodically.
        """
        if not self.discovered_meters:
            return
        
        try:
            # Read the current config
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = safe_load(f)
            
            if config is None:
                config = {}
            
            # Get existing meter IDs
            existing_ids = set()
            if 'meters' in config and config['meters']:
                existing_ids = {str(m['id']) for m in config['meters']}
            else:
                config['meters'] = []
            
            # Add discovered meters that aren't already in config
            added_count = 0
            for meter_id, meter_info in self.discovered_meters.items():
                if meter_id not in existing_ids and added_count < self.max_meters:
                    defaults = get_smart_defaults(
                        meter_id, 
                        meter_info['protocol'], 
                        meter_info['device_class']
                    )
                    config['meters'].append(defaults)
                    added_count += 1
            
            if added_count > 0:
                # Write the updated config back
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    safe_dump(config, f, default_flow_style=False, allow_unicode=True)
                
                if self.logger:
                    self.logger.info('Added %d discovered meters to config file', added_count)
        
        except Exception as e:
            if self.logger:
                self.logger.error('Failed to update config with discovered meters: %s', e)
