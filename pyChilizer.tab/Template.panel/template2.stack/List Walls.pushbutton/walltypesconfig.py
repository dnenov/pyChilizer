# -*- coding: utf-8 -*-


from pyrevit import script, forms, revit, DB
from rpw.ui.forms import (FlexForm, Label, ComboBox, CheckBox, TextBox, Separator, Button)
from pychilizer import units, database
from Autodesk.Revit import Exceptions

op = script.get_output()
op.close_others()

doc = revit.doc

my_config = script.get_config()
DEFAULT_LENGTH = units.round_metric_or_imperial(units.convert_length_to_display(5, doc), doc)
print (my_config.get_option("line_length", doc))
def get_text_types(doc):
    text_types = DB.FilteredElementCollector(
        doc).OfClass(DB.TextNoteType).ToElements()
    dict_text_types = {database.get_name(i): i.Id.IntegerValue for i in text_types}
    return dict_text_types


def get_config(option, doc=revit.doc):
    try:
        if option in ["line_length", "y_offset", "x_offset"]:
            return my_config.get_option(option, DEFAULT_LENGTH)
        else:
            return my_config.get_option(option)
    except AttributeError or Exceptions.AttributeErrorException:
        if option == "line_length":
            return DEFAULT_LENGTH
        elif option == "y_offset":
            return DEFAULT_LENGTH
        elif option == "x_offset":
            return DEFAULT_LENGTH
        elif option == "text_style":
            return get_text_types(doc).values()[0]
        elif option == "include_buildup":
            return False


def rwp_ui_show(doc):
    text_styles_dict = get_text_types()
    prev_text_style_id = DB.ElementId(get_config("text_style"))
    prev_text_style_name = database.get_name(doc.GetElement(prev_text_style_id))
    if prev_text_style_name not in text_styles_dict.keys():
        prev_text_style_name = text_styles_dict.keys()[0]
    components = [
        Label("Wall Length"),
        TextBox(name="line_length", Text=units.convert_length_to_display_string(get_config("line_length", doc))),
        Label("Y Offset"),
        TextBox(name="y_offset", Text=units.convert_length_to_display_string(get_config("y_offset", doc))),
        Label("X Offset"),
        TextBox(name="x_offset", Text=units.convert_length_to_display_string(get_config("x_offset", doc))),
        Label("Text Style"),
        ComboBox(name="text_style", options=text_styles_dict.keys(), default=prev_text_style_name),
        CheckBox("include_buildup", "Include Wall Buildup (Wall layers, thickness, material)",
                 default=bool(get_config("include_buildup"))),
        Button("Remember")
    ]
    form = FlexForm("Settings", components)
    ok = form.show()
    # assign chosen values
    if ok:
        setattr(my_config, "line_length", units.convert_display_string_to_internal(form.values["line_length"], doc))
        setattr(my_config, "y_offset", units.convert_display_string_to_internal(form.values["y_offset"], doc))
        setattr(my_config, "x_offset", units.convert_display_string_to_internal(form.values["x_offset"], doc))
        setattr(my_config, "text_style", text_styles_dict[(form.values["text_style"])])
        setattr(my_config, "include_buildup", int(form.values["include_buildup"]))
        script.save_config()


if __name__ == "__main__":
    rwp_ui_show(doc)
