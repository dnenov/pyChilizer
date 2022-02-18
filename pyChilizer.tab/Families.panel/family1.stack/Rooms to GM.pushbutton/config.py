"""Use FreeForm or Extrusion
"""
# Select between two methods of creating geometry for rooms: Extrusion will create an extrusion based
# on the outline of the room. Freeform will create a non-parameteric shape that is true to room solid.
# An example where this can be useful is when you want to represent a room with sloped top (when attached
# to a roof)

import sys

from pyrevit import script, DB
from rpw.ui.forms import FlexForm, Label, ComboBox, Button

custom_config = script.get_config("Room to GM")

#todo: add location for the template

def get_config():
    prev_cats = custom_config.get_option("chosen_method", [])
    return prev_cats


def config_method():
    prev_choice = get_config()
    opts = ["Extrusion", "Freeform"]
    components = [
        Label("Choose method:"),
        ComboBox(name="method", options=opts, default=prev_choice),
        Button("Remember choice")]

    form = FlexForm("Settings", components)
    ok = form.show()
    if ok:
        res = form.values["method"]

        if res:
            save_config(res)
        return res
    else:
        sys.exit()


def save_config(res):
    custom_config.chosen_method = res
    script.save_config()


if __name__ == "__main__":
    config_method()
