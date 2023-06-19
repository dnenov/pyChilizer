"""List Walls"""

from pyrevit import revit, DB, forms, script

doc = revit.doc
my_config = script.get_config()


LINE_LENGTH = my_config.get_config("line_length")
Y_OFFSET = my_config.get_config("y_offset")
X_OFFSET = my_config.get_config("x_offset")
TXT_TYPE_ID = my_config.get_config("text_style")

INCLUDE_DESCRIPTION = getattr(my_config, "description")


def activate_sym(symbol):
    if symbol.IsActive == False:
        symbol.Activate()


def vb_sym_placer(symbol, point):
    activate_sym(symbol)
    new_vb_sym = doc.Create.NewFamilyInstance(point, symbol, view)
    doc.Regenerate()
    bb = new_vb_sym.get_BoundingBox(view)
    bb_h = bb.Max.Y - bb.Min.Y
    bb_offset_down = DB.XYZ(0, -bb_h, 0)
    point = point.Add(offset)
    point = point.Add(bb_offset_down)
    return new_vb_sym, point


def label_placer(text, point, text_style_id):
    point = point.Add(label_offset)
    text_note = DB.TextNote.Create(doc, view.Id, point, text, text_style_id)
    return text_note


def set_bold(txt_note):
    f = txt_note.GetFormattedText()
    f.SetBoldStatus(True)
    txt_note.SetFormattedText(f)
    return txt_note


# def cb_sym_placer(cb_symbol, point):
#     activate_sym(cb_symbol)
#
#     p1 = point
#     p2 = point.Add(DB.XYZ(LINE_LENGTH, 0, 0))
#
#     curve = DB.Line.CreateBound(p1, p2)
#     new_cb_sym = doc.Create.NewFamilyInstance(curve, cb_sym, view)
#
#     bb = new_vb_sym.get_BoundingBox(view)
#     bb_h = bb.Max.Y - bb.Min.Y
#     bb_offset_down = DB.XYZ(0, -bb_h, 0)
#
#     point = point.Add(offset)
#     point = point.Add(bb_offset_down)
#     return new_cb_sym, point


def get_level_from_view(view):
    levels = DB.FilteredElementCollector(doc).OfClass(DB.Level)
    lvl_param = view.get_Parameter(DB.BuiltInParameter.PLAN_VIEW_LEVEL)

    for lvl in levels:
        if lvl.Name == lvl_param.AsString():
            return lvl


def place_wall(wall, loc, level):
    p1 = loc + DB.XYZ(0, -1, 0)
    p2 = loc.Add(DB.XYZ(LINE_LENGTH, -1, 0))

    curve = DB.Line.CreateBound(p1, p2)
    new_wall = DB.Wall.Create(doc, curve, level.Id, True)
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
    except:
        forms.alert("Cancelled", ok=True, exitscript=True)

coll_wall_types = DB.FilteredElementCollector(doc).OfCategory(
    DB.BuiltInCategory.OST_Walls).WhereElementIsElementType()

dict_walls = {}
layers_count = {}

for wall in coll_wall_types:
    try:
        type_name = wall.get_Parameter(
            DB.BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString()
        if INCLUDE_DESCRIPTION:
            # convert to mm without the ConvertUtils, kind of helps with RevitAPI Changes :/
            type_name += " - Total Thickness {}mm\n".format(wall.Width*25.4*12)
            layers = wall.GetCompoundStructure().GetLayers()
            for layer in layers:
                fonction = layer.Function
                # convert to mm without the ConvertUtils, kind of helps with RevitAPI Changes :/
                width = layer.Width*25.4*12
                material = doc.GetElement(layer.MaterialId).Name
                type_name += "- {}mm - {} - {}\n".format(width, fonction, material)
            if type_name not in dict_walls.keys():
                layers_count[type_name] = len(layers)
        if type_name not in dict_walls.keys():
            dict_walls[type_name] = wall
    except:
        continue

view = revit.active_view
level = get_level_from_view(view)

label_offset = DB.XYZ(X_OFFSET, 0, 0)

with revit.Transaction("Wall Types Legend"):
    for name in sorted(dict_walls):
        try:
            offset = DB.XYZ(0, -Y_OFFSET-layers_count[name], 0)
        except:
            offset = DB.XYZ(0, -Y_OFFSET, 0)
        header = label_placer(name, location, TXT_TYPE_ID)
        set_bold(header)
        new_wall = place_wall(dict_walls[name], location, level)
        change_wall_type(new_wall, dict_walls[name])
        location = location.Add(offset)
