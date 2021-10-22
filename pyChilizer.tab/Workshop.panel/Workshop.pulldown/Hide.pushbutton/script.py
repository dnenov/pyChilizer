from pyrevit import forms
from pyrevit import script
from pyrevit.coreutils import ribbon


__title__ = "Hide\npyRevit"

for tab in ribbon.get_current_ui():
    if tab.name == "pyRevit":
        tab.visible = not tab.visible