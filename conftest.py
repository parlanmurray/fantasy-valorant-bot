import sys
import os

# Allow `pytest backend/test/` to be run from the project root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
