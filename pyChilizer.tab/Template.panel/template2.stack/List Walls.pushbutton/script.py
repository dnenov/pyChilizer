"""List Walls"""

from pyrevit import revit, DB, forms, script
import walltypesconfig
from pychilizer import units
from Autodesk.Revit import Exceptions
import sys

BIC = DB.BuiltInCategory
doc = revit.doc
view = revit.active_view
units_symbol = units.get_length_units_name(doc)

line_length = units.convert_length_to_internal(walltypesconfig.get_config("line_length"), doc)
y_offset = units.convert_length_to_internal(walltypesconfig.get_config("y_offset"), doc)
x_offset = units.convert_length_to_internal(walltypesconfig.get_config("x_offset"), doc)
text_style_id = DB.ElementId(walltypesconfig.get_config("text_style"))
if not doc.GetElement(text_style_id):
    text_style_id = doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType)
include_wall_buildup = walltypesconfig.get_config("include_buildup")



def label_placer(text, point, text_style_id):
    point = point.Add(label_offset)
    text_note = DB.TextNote.Create(doc, view.Id, point, text, text_style_id)
    return text_note


def set_bold(txt_note):
    f = txt_note.GetFormattedText()
    f.SetBoldStatus(True)
    txt_note.SetFormattedText(f)
    return txt_note


def get_level_from_view(view):
    levels = DB.FilteredElementCollector(doc).OfClass(DB.Level)
    lvl_param = view.get_Parameter(DB.BuiltInParameter.PLAN_VIEW_LEVEL)

    for lvl in levels:
        if lvl.Name == lvl_param.AsString():
            return lvl


def place_wall(loc, level):
    p1 = loc + DB.XYZ(0, -1, 0)
    p2 = loc.Add(DB.XYZ(line_length, -1, 0))

    curve = DB.Line.CreateBound(p1, p2)
    try:
        new_wall = DB.Wall.Create(doc, curve, level.Id, True)
    except:
        pass
    return new_wall


def change_wall_type(wall_element, wall_type):
    try:
        wall_element.WallType = wall_type
    except:
        return


with forms.WarningBar(title="Pick Point"):
    try:
        location = revit.uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)
    except Exceptions.InvalidOperationException as ex:
        forms.alert("Error! {}".format(ex.Message), ok=True, exitscript=True)

coll_wall_types = DB.FilteredElementCollector(doc).OfCategory(
    BIC.OST_Walls).WhereElementIsElementType()

dict_walls = {}
layers_count = {}

for wall_type in coll_wall_types:
    try:
        type_name = wall_type.get_Parameter(
            DB.BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString()

        if include_wall_buildup:
            # convert to mm without the ConvertUtils, kind of helps with RevitAPI Changes :/
            type_name += "\n\nTotal Thickness {}{}:".format(units.convert_length_to_display(wall_type.Width, doc),units_symbol)
            layers = wall_type.GetCompoundStructure().GetLayers()
            for layer in layers:
                layer_function = layer.Function
                # convert to mm without the ConvertUtils, kind of helps with RevitAPI Changes :/
                width = layer.Width * 25.4 * 12
                material = doc.GetElement(layer.MaterialId).Name
                type_name += "\n\t- {}{} - {} - {}".format(width, units_symbol,layer_function, material)
            if type_name not in dict_walls.keys():
                layers_count[type_name] = len(layers)
        if type_name not in dict_walls.keys():

            dict_walls[type_name] = wall_type
    except:
        continue

label_offset = DB.XYZ(x_offset, 0, 0)
with revit.Transaction("Wall Types Legend"):
    if view.ViewType == DB.ViewType.Legend:
        source_legend_component = DB.FilteredElementCollector(doc, view.Id).OfCategory(
            BIC.OST_LegendComponents).FirstElement()
        forms.alert_ifnot(source_legend_component,
                          "The legend must have at least one source Legend Component to copy",
                          exitscript=True)
        source_bb = source_legend_component.get_BoundingBox(view)
        initial_translation = - (source_bb.Max + source_bb.Min)/2

    elif view.ViewType == DB.ViewType.FloorPlan:
        level = get_level_from_view(view)
    for name in sorted(dict_walls):
        try:
            offset = DB.XYZ(0, -y_offset - layers_count[name], 0)
        except KeyError:
            offset = DB.XYZ(0, -y_offset, 0)
        header = label_placer(name, location, text_style_id)
        set_bold(header)

        if view.ViewType == DB.ViewType.Legend:

            copy_component_id = \
                DB.ElementTransformUtils.CopyElement(doc, source_legend_component.Id, initial_translation)[0]
            new_component = doc.GetElement(copy_component_id)
            wall_type = dict_walls[name]

            new_component.get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT).Set(wall_type.Id)
            new_component.get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT_VIEW).Set(-8)
            new_component.get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT_LENGTH).Set(line_length)
            wall_thickness = wall_type.Width
            DB.ElementTransformUtils.MoveElement(doc, new_component.Id, location - DB.XYZ(0, wall_thickness/2, 0))
            location = location.Add(offset)

        elif view.ViewType == DB.ViewType.FloorPlan:
            new_wall = place_wall(location, level)
            change_wall_type(new_wall, dict_walls[name])
            location = location.Add(offset)
