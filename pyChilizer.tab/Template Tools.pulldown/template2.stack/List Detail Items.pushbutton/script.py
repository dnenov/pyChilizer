"""List Detail Items"""

from pyrevit import revit, DB, UI, HOST_APP, forms, script
from collections import OrderedDict
from Autodesk.Revit import Exceptions
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)

# TODO: Add text style config


def get_any_text_type_id():
    # get a default text note type - to replace later
    txt_type = revit.doc.GetElement(revit.doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType))
    return txt_type.Id


def activate_sym(symbol):
    if symbol.IsActive == False:
        symbol.Activate()


def vb_sym_placer(symbol, point):
    activate_sym(symbol)
    new_vb_sym = revit.doc.Create.NewFamilyInstance(point, symbol, view)
    revit.doc.Regenerate()
    bb = new_vb_sym.get_BoundingBox(view)
    bb_h = bb.Max.Y - bb.Min.Y
    bb_offset_down = DB.XYZ(0, -bb_h, 0)
    point = point.Add(offset)
    point = point.Add(bb_offset_down)
    return new_vb_sym, point


def label_placer(text, point, text_style_id):
    point = point.Add(label_offset)
    text_note = DB.TextNote.Create(revit.doc, view.Id, point, text, text_style_id)
    return text_note


def set_bold(txt_note):
    f = txt_note.GetFormattedText()
    f.SetBoldStatus(True)
    txt_note.SetFormattedText(f)
    return txt_note


def cb_sym_placer(cb_symbol, point):
    activate_sym(cb_symbol)

    p1 = point
    p2 = point.Add(DB.XYZ(line_length, 0, 0))

    curve = DB.Line.CreateBound(p1, p2)
    new_cb_sym = revit.doc.Create.NewFamilyInstance(curve, cb_sym, view)

    bb = new_vb_sym.get_BoundingBox(view)
    bb_h = bb.Max.Y - bb.Min.Y
    bb_offset_down = DB.XYZ(0, -bb_h, 0)

    point = point.Add(offset)
    point = point.Add(bb_offset_down)
    return new_cb_sym, point


with forms.WarningBar(title="Pick Point"):
    try:
        location = revit.uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)

coll_dc_types = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_DetailComponents).OfClass(
    DB.FamilySymbol).WhereElementIsElementType()

dc_viewbased = [dc for dc in coll_dc_types if dc.Family.FamilyPlacementType == DB.FamilyPlacementType.ViewBased]
dc_curvebased = [dc for dc in coll_dc_types if dc.Family.FamilyPlacementType == DB.FamilyPlacementType.CurveBasedDetail]

dict_vb = {}
dict_cb = {}

for sym in dc_viewbased:
    fam = sym.get_Parameter(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM).AsString()
    typ = sym.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
    if fam not in dict_vb.keys():
        dict_vb[fam] = {}
    dict_vb[fam][typ] = sym

for sym in dc_curvebased:
    fam = sym.get_Parameter(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM).AsString()
    typ = sym.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
    if fam not in dict_cb.keys():
        dict_cb[fam] = {}
    dict_cb[fam][typ] = sym


view = revit.active_view

line_length = 2
y_offset = 1
x_offset = 2


offset = DB.XYZ(0, -y_offset, 0)
label_offset = DB.XYZ(x_offset, 0,0)



with revit.Transaction("Place Detail Items"):
    for dc_fam in sorted(dict_vb):

        fam_name = " : ".join(["Family", dc_fam])
        header = label_placer(fam_name, location, get_any_text_type_id())
        set_bold(header)
        location = location.Add(offset)

        for typ in sorted(dict_vb[dc_fam]):
            vb_sym = dict_vb[dc_fam][typ]
            new_vb_sym, shift_down  = vb_sym_placer(vb_sym, location)
            type_name = " : ".join(["Type", typ])
            label_placer(type_name, location, get_any_text_type_id())
            location = shift_down

        location = location.Add(offset)

    for dc_fam in sorted(dict_cb):

        fam_name = " : ".join(["Family", dc_fam])
        header = label_placer(fam_name, location, get_any_text_type_id())
        set_bold(header)
        location = location.Add(offset)

        for typ in sorted(dict_cb[dc_fam]):
            cb_sym = dict_cb[dc_fam][typ]
            new_cb_sym, shift_down = cb_sym_placer(cb_sym, location)
            type_name = " : ".join(["Type", typ])
            label_placer(type_name, location, get_any_text_type_id())
        location = location.Add(offset)

