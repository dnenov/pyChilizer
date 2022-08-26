"""List Walls"""

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


def get_level_from_view(view):
    levels = DB.FilteredElementCollector(revit.doc).OfClass(DB.Level)
    lvl_param = view.LookupParameter("Associated Level")

    for lvl in levels:
        if lvl.Name == lvl_param.AsString():
            return lvl


def place_wall(wall, loc, level):
    p1 = loc + DB.XYZ(0, -1, 0)
    p2 = loc.Add(DB.XYZ(line_length, -1, 0))

    curve = DB.Line.CreateBound(p1, p2)
    new_wall = DB.Wall.Create(revit.doc, curve, level.Id, True)
    return new_wall
    # new_wall.WallType = wall


def change_wall_type(wall, wall_type):
    try:
        wall.WallType = wall_type
    except:
        return

with forms.WarningBar(title="Pick Point"):
    try:
        location = revit.uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)

coll_wall_types = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_Walls).WhereElementIsElementType()

dict_walls = {}

for wall in coll_wall_types:
    try:
        type_name = DB.Element.Name.GetValue(wall)
        if type_name not in dict_walls.keys():
            dict_walls[type_name] = wall
    except:
        continue

view = revit.active_view
level = get_level_from_view(view)

line_length = 6
y_offset = 3
x_offset = 2

offset = DB.XYZ(0, -y_offset, 0)
label_offset = DB.XYZ(x_offset, 0,0)


with revit.Transaction("Place Detail Items"):
    for name in sorted(dict_walls):
        header = label_placer(name, location, get_any_text_type_id())
        set_bold(header)
        new_wall = place_wall(dict_walls[name], location, level)
        change_wall_type(new_wall, dict_walls[name])
        location = location.Add(offset)

