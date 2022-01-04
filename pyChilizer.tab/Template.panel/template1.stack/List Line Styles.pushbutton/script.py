"""List Line Styles"""

from pyrevit import revit, DB, forms, HOST_APP
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button, TextBox)
from collections import OrderedDict
from Autodesk.Revit import Exceptions
import sys


def convert_length_to_internal(d_units):
    # convert length units from display units to internal
    units = revit.doc.GetUnits()
    if HOST_APP.is_newer_than(2021):
        internal_units = units.GetFormatOptions(DB.SpecTypeId.Length).GetUnitTypeId()
    else: # pre-2021
        internal_units = units.GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
    converted = DB.UnitUtils.ConvertToInternalUnits(d_units, internal_units)
    return converted


# pick text style
txt_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.TextNoteType)
text_style_dict= {txt_t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString(): txt_t for txt_t in txt_types}
# construct rwp UI
components = [
    Label("Pick Text Style:"),
    ComboBox(name="textstyle_combobox", options=text_style_dict),
    Label("Vertical Offset:"),
    TextBox(name="offset", Text="500"),
    Button("Select")]
form = FlexForm("Appearance", components)
ok = form.show()
if ok:
    # assign chosen values
    chosen_text_style = form.values["textstyle_combobox"]
    vert_offset = float(form.values["offset"])
else:
    sys.exit()

cat = revit.doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_Lines)
subcats = [subcat for subcat in cat.SubCategories]

# create ordered dictionary
unsorted_dict = {}
for sc in subcats:
    unsorted_dict[sc] = sc.Name

sorted_subcats = OrderedDict(sorted(unsorted_dict.items(), key=lambda t:t[1]))


view = revit.active_view

# dims and scale
scale = float(view.Scale)/ 100
w = 20 * scale
text_offset = 1 * scale
shift = convert_length_to_internal(vert_offset) * scale

with forms.WarningBar(title="Pick Point"):
    try:
        pick_point = revit.uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)

p1 = pick_point
p2 = DB.XYZ(pick_point.X+w, pick_point.Y, 0)

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