# -*- coding: utf-8 -*-


from pyrevit import script, forms, revit, DB
from pyrevit.compat import get_elementid_value_func
from rpw.ui.forms import (FlexForm, Label, ComboBox, CheckBox, TextBox, Separator, Button)
from pychilizer import units, database
from Autodesk.Revit import Exceptions

op = script.get_output()
op.close_others()

doc = revit.doc

get_elementid_value = get_elementid_value_func()

my_config = script.get_config()
DEFAULT_LENGTH = 5

def get_text_types(doc):
    text_types = DB.FilteredElementCollector(
        doc).OfClass(DB.TextNoteType).ToElements()
    dict_text_types = {database.get_name(i): get_elementid_value(i.Id) for i in text_types}
    return dict_text_types


def get_config(option, doc=revit.doc):
    try:
        if option in [""]:
            return my_config.get_option(option, DEFAULT_LENGTH)
        else:
            return my_config.get_option(option)
    except AttributeError or Exceptions.AttributeErrorException:
        if option == "v_offset":
            return DEFAULT_LENGTH
        elif option == "text_style":
            return get_text_types(doc).values()[0]
        elif option == "text_bold":
            return False
        elif option == "include_buildup":
            return False


def rwp_ui_show(doc):
    text_styles_dict = get_text_types(doc)
    prev_text_style_id = DB.ElementId(get_config("text_style"))
    prev_text_style_name = database.get_name(doc.GetElement(prev_text_style_id))
    v_offset_dict = ["Compact","Spaced"]


    if prev_text_style_name not in text_styles_dict.keys():
        prev_text_style_name = text_styles_dict.keys()[0]
    components = [
        Label("Vertical Offset"),
        ComboBox(name="v_offset_combobox", options=v_offset_dict),
        Label("Text Style"),
        ComboBox(name="text_style", options=text_styles_dict.keys(), default=prev_text_style_name),
        CheckBox("text_bold", "Text Bold",
                 default=bool(get_config("include_buildup"))),
        CheckBox("include_buildup", "Include Wall Buildup (Wall layers, thickness, material)", default=bool(get_config("include_buildup"))),
        Button("Remember")
    ]
    form = FlexForm("Settings", components)
    ok = form.show()
    # assign chosen values
    if ok:
        setattr(my_config, "v_offset", form.values["v_offset_combobox"])
        setattr(my_config, "text_style", text_styles_dict[(form.values["text_style"])])
        setattr(my_config, "text_bold", int(form.values["text_bold"]))
        setattr(my_config, "include_buildup", int(form.values["include_buildup"]))
        script.save_config()


if __name__ == "__main__":
    rwp_ui_show(doc)
