# -*- coding: utf-8 -*-
from pyrevit import script, forms, revit, DB
from rpw.ui.forms import (FlexForm, Label, ComboBox, CheckBox, TextBox, Separator, Button)
from pychilizer import units, database
from Autodesk.Revit import Exceptions

op = script.get_output()
op.close_others()

doc = revit.doc

my_config = script.get_config()
DEFAULT_WALL_LENGTH = round(units.convert_length_to_display(5, doc), -2)
DEFAULT_Y_OFFSET = round(units.convert_length_to_display(5, doc), -2)
DEFAULT_X_OFFSET = round(units.convert_length_to_display(5, doc), -2)


# def config_setter(low, high, prompt, param):
#     rows = [str(i) for i in range(low, high)]
#     form = forms.SelectFromList.show(
#         rows, title=prompt, height=425, width=350
#     )
#     if form:
#         setattr(my_config, param, int(form))
#         script.save_config()
#     else:
#         setattr(my_config, param, high)
#         script.save_config()


def get_text_types():
    text_types = DB.FilteredElementCollector(
        doc).OfClass(DB.TextNoteType).ToElements()
    dict_text_types = {database.get_name(i):i.Id.IntegerValue for i in text_types}
    return dict_text_types


# def text_config_setter(prompt, param):
#     text_types = DB.FilteredElementCollector(
#         doc).OfClass(DB.TextNoteType).ToElements()
#     dict_text_types = {i.get_Parameter(
#         DB.BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString(): i for i in text_types}
#     form = forms.SelectFromList.show(
#         dict_text_types.keys(), title=prompt, height=425, width=350
#     )
#     if form:
#         setattr(my_config, param, int(str(dict_text_types[form].Id)))
#         script.save_config()
#     else:
#         setattr(my_config, param, int(
#             str(doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType))))
#         script.save_config()


# def include_description():
#     form = forms.alert("Do you want to include the description (thickness, layer, material) of the wall composition?",
#                        title='include description', warn_icon=False, yes=True, no=True, ok=False)
#     if form:
#         setattr(my_config, "INCLUDE_DESCRIPTION", True)
#         script.save_config()
#     else:
#         setattr(my_config, "INCLUDE_DESCRIPTION", False)
#         script.save_config()


def get_config(option):
    try:
        if option in ["line_length", "y_offset", "x_offset"]:
            return units.convert_length_to_display(my_config.get_option(option))
        else:
            return my_config.get_option(option)
    except AttributeError or Exceptions.AttributeErrorException:
        if option == "line_length":
            return DEFAULT_WALL_LENGTH
        elif option == "y_offset":
            return DEFAULT_Y_OFFSET
        elif option == "x_offset":
            return DEFAULT_X_OFFSET
        elif option == "text_style":
            return get_text_types().values()[0]
        elif option == "description":
            return False


def rwp_ui_show():
    text_styles_dict = get_text_types()
    prev_text_style_id = DB.ElementId(get_config("text_style"))
    prev_text_style_name = database.get_name(doc.GetElement(prev_text_style_id))
    components = [
        Label("Wall Length"),
        TextBox(name="line_length", Text=str(get_config("line_length"))),
        Label("Y Offset"),
        TextBox(name="y_offset", Text=str(get_config("y_offset"))),
        Label("X Offset"),
        TextBox(name="x_offset", Text=str(get_config("x_offset"))),
        Label("Text Style"),
        ComboBox(name="text_style", options=text_styles_dict.keys(), default=prev_text_style_name),
        CheckBox("description", "Include Description (Wall layers, thickness, material)",
                 default=bool(get_config("description"))),
        Button("Remember")
    ]
    form = FlexForm("Settings", components)
    ok = form.show()
    # assign chosen values
    if ok:
        setattr(my_config, "line_length", units.convert_length_to_internal(float(form.values["line_length"])))
        setattr(my_config, "y_offset", units.convert_length_to_internal(float(form.values["y_offset"])))
        setattr(my_config, "x_offset", units.convert_length_to_internal(float(form.values["x_offset"])))
        setattr(my_config, "text_style", text_styles_dict[(form.values["text_style"])])
        setattr(my_config, "description", int(form.values["description"]))
        script.save_config()


if __name__ == "__main__":
    rwp_ui_show()