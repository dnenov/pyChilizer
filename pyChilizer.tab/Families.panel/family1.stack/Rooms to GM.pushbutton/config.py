"""Use FreeForm or Extrusion
"""

from pyrevit import revit, script, DB, forms

# config = script.get_config()
custom_config = script.get_config("Room to GM")


class PrevSelectedItem(forms.TemplateListItem):
    pass


def get_config():
    prev_cats = custom_config.get_option("chosen_method", [])
    # options = {"Extrusion": True, "FreeForm": False}
    return prev_cats


def config_method():
    prev_choice = get_config()
    opts = ["Extrusion", "FreeForm"]
    res = forms.SelectFromList.show([PrevSelectedItem(
        op,
        checkable=True,
        checked=False)
        for op in opts],

        title="Select Transformation Method",
        button_name="Apply",
        height=250,
        width=400
    )
    if res:
        save_config(res)
    return res


def save_config(res):
    custom_config.chosen_method = res
    script.save_config()


if __name__ == "__main__":
    config_method()
