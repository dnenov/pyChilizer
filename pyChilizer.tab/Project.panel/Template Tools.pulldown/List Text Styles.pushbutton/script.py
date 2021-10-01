"""List Text Styles"""

from pyrevit import revit, DB, forms
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
from collections import OrderedDict

# pick text style
txt_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.TextNoteType)
text_style_dict= {txt_t: txt_t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() for txt_t in txt_types}

# sort styles by name
sorted_text_styles = OrderedDict(sorted(text_style_dict.items(), key=lambda t:t[1]))
view = revit.active_view

# dims and scale
scale = float(view.Scale)/ 200
shift = 5 * scale
offset = 0

text_height = 0
with revit.Transaction("Place Text Notes"):
    for ts in sorted_text_styles:

        label_text = sorted_text_styles[ts]

#        print (sorted_text_styles[ts],text_height*304, offset )
        text_position = DB.XYZ(0, -offset,0)
        text_height = ts.get_Parameter(DB.BuiltInParameter.TEXT_SIZE).AsDouble()
        offset += (text_height * 2.75 * float(view.Scale))
        text_note = DB.TextNote.Create(revit.doc, view.Id, text_position, label_text, ts.Id)