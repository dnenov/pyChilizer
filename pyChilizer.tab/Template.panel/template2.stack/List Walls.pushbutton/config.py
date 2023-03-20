# -*- coding: utf-8 -*-
from pyrevit import script, forms, revit, DB

op = script.get_output()
op.close_others()

doc = revit.doc

my_config = script.get_config()


def config_setter(low, high, prompt, param):
    rows = [str(i) for i in range(low, high)]
    form = forms.SelectFromList.show(
        rows, title=prompt, height=425, width=350
    )
    if form:
        setattr(my_config, param, int(form))
        script.save_config()
    else:
        setattr(my_config, param, high)
        script.save_config()


def text_config_setter(prompt, param):
    text_types = DB.FilteredElementCollector(
        doc).OfClass(DB.TextNoteType).ToElements()
    dict_text_types = {i.get_Parameter(
        DB.BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString(): i for i in text_types}
    form = forms.SelectFromList.show(
        dict_text_types.keys(), title=prompt, height=425, width=350
    )
    if form:
        setattr(my_config, param, int(str(dict_text_types[form].Id)))
        script.save_config()
    else:
        setattr(my_config, param, int(
            str(doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType))))
        script.save_config()


if __name__ == "__main__":
    config_setter(1, 6, "Wall Length", "LINE_LENGTH")
    config_setter(1, 6, "Y Offset", "Y_OFFSET")
    config_setter(1, 6, "X Offset", "X_OFFSET")
    text_config_setter("Text Style", "TXT_TYPE_ID")
