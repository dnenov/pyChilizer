"""List Filled Regions"""

from pyrevit import revit, DB, UI, HOST_APP, forms
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button, TextBox)
from collections import OrderedDict
from pyrevit.framework import List
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


view = revit.active_view

coll_fill_reg = DB.FilteredElementCollector(revit.doc).OfClass(DB.FilledRegionType)

unsorted_dict = {fr:fr.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() for fr in coll_fill_reg}
sorted_fillreg = OrderedDict(sorted(unsorted_dict.items(), key=lambda t:t[1]))

# get all text styles to choose from
txt_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.TextNoteType)
text_style_dict= {txt_t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString(): txt_t for txt_t in txt_types}

# construct rwp UI
components = [
    Label("Pick Text Style"),
    ComboBox(name="textstyle_combobox", options=text_style_dict),
    Label("Box Width [mm]"),
    TextBox(name="box_width", Text="800"),
    Label("Box Height [mm]"),
    TextBox(name="box_height", Text="300"),
    Label("Offset [mm]"),
    TextBox(name="box_offset", Text="100"),
    Button("Select")
]
form = FlexForm("Select", components)
ok = form.show()
if ok:
    # assign chosen values
    text_style = form.values["textstyle_combobox"]
    box_width = int(form.values["box_width"])
    box_height = int(form.values["box_height"])
    box_offset = int(form.values["box_offset"])
else:
    sys.exit()

# dims and scale
scale = float(view.Scale)/ 100
w = convert_length_to_internal(box_width) * scale
h = convert_length_to_internal(box_height) * scale
text_offset = 1 * scale
shift = (convert_length_to_internal(box_offset + box_height)) * scale


with forms.WarningBar(title="Pick Point"):
    try:
        pt = revit.uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)


# create rectrangle
crv_loop = DB.CurveLoop()

p1 = DB.XYZ(pt.X, pt.Y, 0)
p2 = DB.XYZ(pt.X+w, pt.Y, 0)
p3 = DB.XYZ(pt.X+w, pt.Y+h, 0)
p4 = DB.XYZ(pt.X, pt.Y+h, 0)

# create lines between points
l1 = DB.Line.CreateBound(p1, p2)
l2 = DB.Line.CreateBound(p2, p3)
l3 = DB.Line.CreateBound(p3, p4)
l4 = DB.Line.CreateBound(p4, p1)

rectangle = [l1, l2, l3, l4]

with revit.Transaction("Draw Filled Regions"):
    for fr in sorted_fillreg:

        t1 = DB.Transform.CreateTranslation(DB.XYZ(0, -shift, 0))
        rectangle = [line.CreateTransformed(t1) for line in rectangle]
        crv_loop = DB.CurveLoop.Create(List[DB.Curve](rectangle))

        # draw rectangles with filled region
        new_reg = DB.FilledRegion.Create(revit.doc, fr.Id, view.Id, [crv_loop])

        # place text next to filled regions
        t2 = DB.Transform.CreateTranslation(DB.XYZ(text_offset, 0, 0))
        label_position = rectangle[1].CreateTransformed(t2).GetEndPoint(1)
        label_txt = sorted_fillreg[fr]
        text_note = DB.TextNote.Create(revit.doc, view.Id, label_position, label_txt, text_style.Id)

