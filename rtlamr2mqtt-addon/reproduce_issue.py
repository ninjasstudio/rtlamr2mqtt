
from app.helpers.monitor_mode import MonitorModeTracker, guess_meter_type
import os

# Mock logger
class MockLogger:
    def info(self, msg, *args):
        print(f"INFO: {msg % args}")
    def warning(self, msg, *args):
        print(f"WARNING: {msg % args}")
    def error(self, msg, *args):
        print(f"ERROR: {msg % args}")

# Create a dummy config file
with open('dummy_config.yaml', 'w') as f:
    f.write("meters: []")

tracker = MonitorModeTracker('dummy_config.yaml', logger=MockLogger())

print("Testing guess_meter_type with int protocol...")
try:
    guess_meter_type(123, 100)
    print("guess_meter_type(123) worked (unexpected if it expects string methods)")
except AttributeError as e:
    print(f"Caught expected error in guess_meter_type: {e}")
except Exception as e:
    print(f"Caught unexpected error in guess_meter_type: {e}")

print("\nTesting add_meter with int protocol...")
try:
    tracker.add_meter("12345", 123, 100)
    print("add_meter worked")
except AttributeError as e:
    print(f"Caught expected error in add_meter: {e}")
except Exception as e:
    print(f"Caught unexpected error in add_meter: {e}")

# Cleanup
if os.path.exists('dummy_config.yaml'):
    os.remove('dummy_config.yaml')
if os.path.exists('dummy_config_discovered.yaml'):
    os.remove('dummy_config_discovered.yaml')
