from .settings import settings, AppSettings, load_settings

# Import Config from the root config.py file
import sys
import os

# Add the parent directory to sys.path to access root config.py
root_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, root_dir)

# Import from the root config.py file explicitly
import config as root_config
Config = root_config.Config


def get_config():
  return Config


__all__ = ['settings', 'AppSettings', 'load_settings', 'Config']
