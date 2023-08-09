from pyrevit import script, revit
from pychilizer import colorize, database

overrides_config = script.get_config() #get colorizebyvalue config - to store override options

def get_overrides_config():
    return colorize.get_config(overrides_config, colorize.OVERRIDES_CONFIG_OPTION_NAME, colorize.default_override_options)


if __name__ == "__main__":
    colorize.config_overrides(overrides_config, colorize.OVERRIDES_CONFIG_OPTION_NAME)
    colorize.config_category_overrides(revit.doc)
