"""Use FreeForm or Extrusion
"""

from pyrevit import revit, script, DB, forms
from rpw.ui.forms import FlexForm, Label, ComboBox, Button
# config = script.get_config()
custom_config = script.get_config("Room to GM")


def get_config():
    prev_cats = custom_config.get_option("chosen_method", [])
    return prev_cats


def config_method():
    prev_choice = get_config()
    opts = ["Extrusion", "Freeform"]
    components = [
        Label("Choose method:"),
        ComboBox(name="method", options=opts, default=prev_choice),
        Button("Remember")]

    form = FlexForm("Settings", components)
    form.show()
    res = form.values["method"]

    if res:
        save_config(res)
    return res


def save_config(res):
    custom_config.chosen_method = res
    script.save_config()


if __name__ == "__main__":
    config_method()
