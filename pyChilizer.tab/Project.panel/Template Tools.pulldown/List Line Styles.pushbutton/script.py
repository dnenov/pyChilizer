"""List Line Styles"""

from pyrevit import revit, DB, forms
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
from collections import OrderedDict

# pick text style
txt_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.TextNoteType)
text_style_dict= {txt_t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString(): txt_t for txt_t in txt_types}
# construct rwp UI
components = [
    Label("Pick Text Style:"),
    ComboBox(name="textstyle_combobox1", options=text_style_dict),
    Button("Select")]
form = FlexForm("Appearance", components)
form.show()
# assign chosen values
chosen_text_style = form.values["textstyle_combobox1"]


cat = revit.doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_Lines)
subcats = [subcat for subcat in cat.SubCategories]

# create ordered dictionary
unsorted_dict = {}
for sc in subcats:
    unsorted_dict[sc] = sc.Name

sorted_subcats = OrderedDict(sorted(unsorted_dict.items(), key=lambda t:t[1]))


view = revit.active_view
# TODO: filter only relevant views

# dims and scale
scale = float(view.Scale)/ 200
w = 8 * scale
text_offset = 1 * scale
shift = 5 * scale


p1 = DB.XYZ(0, 0, 0)
p2 = DB.XYZ(w, 0, 0)

# create lines between points
l1 = DB.Line.CreateBound(p1, p2)

with revit.Transaction("Draw Lines"):
    for ls in sorted_subcats.keys():

        t1 = DB.Transform.CreateTranslation(DB.XYZ(0, -shift, 0))
        l1 = l1.CreateTransformed(t1)
        new_line = revit.doc.Create.NewDetailCurve (view, l1)
        gs = ls.GetGraphicsStyle(DB.GraphicsStyleType.Projection)
        new_line.LineStyle = gs

        label_text = sorted_subcats[ls]
        t2 = DB.Transform.CreateTranslation(DB.XYZ(text_offset, 0, 0))
        text_position = l1.CreateTransformed(t2).GetEndPoint(1)

        text_note = DB.TextNote.Create(revit.doc, view.Id, text_position, label_text, chosen_text_style.Id)