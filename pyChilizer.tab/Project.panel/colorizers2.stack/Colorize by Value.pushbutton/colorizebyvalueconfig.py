from pyrevit import script
from pychilizer import colorize

custom_config = script.get_config()
def get_config():
    return colorize.get_config(custom_config)

if __name__ == "__main__":
    colorize.config_overrides(custom_config)
