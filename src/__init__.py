import os
import sys

# Add the vendored streamrip to the Python path
vendor_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vendor", "streamrip")
if os.path.isdir(vendor_path):
    sys.path.insert(0, vendor_path)
