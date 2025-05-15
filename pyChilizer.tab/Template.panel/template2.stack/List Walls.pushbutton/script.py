"""List Walls"""

from pyrevit import revit, DB, forms, script
import walltypesconfig
from pychilizer import units
from Autodesk.Revit import Exceptions
import sys

BIC = DB.BuiltInCategory
doc = revit.doc
view = revit.active_view

# read previous configurations or use default
LINE_LENGTH = 7.5  # wall length
TEXT_OFFSET = 8.5
COMPACT_OFFSET = 2.5
SPACED_OFFSET = 5

# -- Configuration settings --
v_offset_choice = walltypesconfig.get_config("v_offset", doc)  # vertical offset choice between Compact and Spaced
v_offset = COMPACT_OFFSET if v_offset_choice == "Compact" else SPACED_OFFSET
text_bold_choice = walltypesconfig.get_config("text_bold")  # Bold text
text_style_id = DB.ElementId(walltypesconfig.get_config("text_style"))  # Selected text style
if not doc.GetElement(text_style_id):
    text_style_id = doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType)
include_wall_buildup = walltypesconfig.get_config("include_buildup")  # Buildup included


# -- Helper Functions --
def label_placer(text, point, t_style_id):
    point = point.Add(label_offset)
    text_note = DB.TextNote.Create(doc, view.Id, point, text, t_style_id)
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


def place_wall(loc, view_level):
    p1 = loc + DB.XYZ(0, -1, 0)
    p2 = loc.Add(DB.XYZ(LINE_LENGTH, -1, 0))

    curve = DB.Line.CreateBound(p1, p2)
    try:
        new_wall_element = DB.Wall.Create(doc, curve, view_level.Id, True)
        return new_wall_element
    except Exception as e:
        print ("Error placing wall: {}".format(e))
        pass


def change_wall_type(wall_element, w_type):
    try:
        wall_element.WallType = w_type
    except Exception as e:
        print("Error changing wall type for wall {} : {}".format(w_type.ToString(), e))
        pass


def format_wall_layers(wall_type, doc):
    description = "\n\nTotal Thickness {}:".format(units.convert_length_to_display_string(wall_type.Width, doc))
    wall_structure = wall_type.GetCompoundStructure()
    if wall_structure:
        for layer in wall_structure.GetLayers():
            width = units.convert_length_to_display_string(layer.Width, doc)
            material = doc.GetElement(layer.MaterialId)
            material_name = material.Name if material else "ByCategory"
            description += "\n\t- {} - {} - {}".format(width, layer.Function, material_name)
    return description


with forms.WarningBar(title="Pick Point"):
    try:
        location = revit.uidoc.Selection.PickPoint()
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, exitscript=True)
    except Exceptions.InvalidOperationException as ex:
        forms.alert("Error! {}".format(ex.Message), ok=True, exitscript=True)

coll_wall_types = DB.FilteredElementCollector(doc) \
    .OfCategory(BIC.OST_Walls) \
    .OfClass(DB.WallType) \
    .WhereElementIsElementType()

dict_walls = {}
layers_count = {}

for wall_type in coll_wall_types:
    if wall_type.Kind.ToString() == "Basic":  # discard Curtain and Stacked walls
        type_name = wall_type.get_Parameter(
            DB.BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString()
        if include_wall_buildup:
            type_name += format_wall_layers(wall_type, doc)
            layers_count[type_name] = len(wall_type.GetCompoundStructure().GetLayers()) if wall_type.GetCompoundStructure() else 1
        dict_walls.setdefault(type_name, wall_type)

label_offset = DB.XYZ(TEXT_OFFSET, 0, 0)  # initial offset

with revit.Transaction("Wall Types Legend"):
    # for legend views - place legend components
    if view.ViewType == DB.ViewType.Legend:
        source_legend_component = DB.FilteredElementCollector(doc, view.Id).OfCategory(
            BIC.OST_LegendComponents).FirstElement()
        forms.alert_ifnot(source_legend_component,
                          "The legend must have at least one source Legend Component to copy. Please place any Legend "
                          "Component on this legend (it can be deleted later).",
                          exitscript=True)
        source_bb = source_legend_component.get_BoundingBox(view)
        initial_translation = - (source_bb.Max + source_bb.Min) / 2
    # for Floor Plan views
    elif view.ViewType == DB.ViewType.FloorPlan:
        level = get_level_from_view(view)
    for name in sorted(dict_walls):
        if include_wall_buildup:  # larger offset if Wall Buildup is included
            if layers_count[name] == 1:
                vertical_offset = v_offset * 1.5
            else:
                vertical_offset = v_offset * layers_count[name]
        else:
            vertical_offset = v_offset

        offset = DB.XYZ(0, -vertical_offset, 0)
        header = label_placer(name, location, text_style_id)
        if text_bold_choice == 1:
            set_bold(header)

        # for Legend views
        if view.ViewType == DB.ViewType.Legend:
            copy_component_id = \
                DB.ElementTransformUtils.CopyElement(doc, source_legend_component.Id, initial_translation)[0]
            new_component = doc.GetElement(copy_component_id)
            wall_type = dict_walls[name]

            new_component.get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT).Set(wall_type.Id)
            new_component.get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT_VIEW).Set(-8)
            new_component.get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT_LENGTH).Set(LINE_LENGTH)
            wall_thickness = wall_type.Width
            DB.ElementTransformUtils.MoveElement(doc, new_component.Id, location - DB.XYZ(0, wall_thickness / 2, 0))
            location = location.Add(offset)

        # for Floor Plan views
        elif view.ViewType == DB.ViewType.FloorPlan:
            new_wall = place_wall(location, level)
            change_wall_type(new_wall, dict_walls[name])
            location = location.Add(offset)
