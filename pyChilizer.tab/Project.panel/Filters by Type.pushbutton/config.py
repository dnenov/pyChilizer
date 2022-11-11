from pyrevit import script, DB
from rpw.ui.forms import FlexForm, Label, CheckBox, Button
import sys


custom_config = script.get_config("Override Options")

def get_config():
    return


def config_overrides():
    previous_choise = get_config()
    opts = ["Projection Line Colour","Projection Surface Colour","Cut Line Colour", "Cut Pattern Colour" ]
    components = [
        Label("Choose Override Options:"),
        CheckBox(name="ovrd_proj_line", checkbox_text="Projection Line Colour", default = proj_line )
    ]