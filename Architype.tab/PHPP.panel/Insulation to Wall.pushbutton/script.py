__title__ = "Insulation\nto Wall"
__doc__ = "Creates a new wall representing the insulation layer"

from pyrevit import revit, DB, script, forms
from pyrevit.framework import List
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)

# get document length units for conversion later
d_units = DB.Document.GetUnits(revit.doc).GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits


def wall_type_has_ins(w_type):
    # return true if wall has insulation layer(s)
    # get compound structure
    compound_str = w_type.GetCompoundStructure()
    wall_has_insulation = False
    # iterate through layers
    num = compound_str.LayerCount
    for n in range(num - 1):
        # if encounter ins layer - wall has ins layer
        if str(compound_str.GetLayerFunction(n)) == "Insulation":
            wall_has_insulation = True
        else:
            pass
    return wall_has_insulation


def get_ins_layer_width(w_type):
    # get widths of insulation layers
    # check if wall has ins
    if wall_type_has_ins(w_type):
        # get compound structure
        comp_str = w_type.GetCompoundStructure()
        # iterate through layers and not down widths of insulation layers
        num = comp_str.LayerCount
        for n in range(num-1):
            if str(comp_str.GetLayerFunction(n)) == "Insulation":
                ins_width = comp_str.GetLayerWidth(n)
                return ins_width
    else:
        return


def get_ins_position(w_type):
    # position of ins layer
    ins_layer_position = 0
    # check if wall has ins
    if wall_type_has_ins(w_type):
        # get compound structure
        comp_str = w_type.GetCompoundStructure()
        # iterate through layers and add up the widths of insulation layers
        num = comp_str.LayerCount
        for n in range(num-1):
            if str(comp_str.GetLayerFunction(n)) != "Insulation":
                ins_layer_position += comp_str.GetLayerWidth(n)
            else:
                return ins_layer_position
        return ins_layer_position
    else:
        return


def convert_units(from_units, to_units=d_units):
    # convert internal to project units

    converted = DB.UnitUtils.ConvertFromInternalUnits(from_units, to_units)
    return converted


def get_hosted(host_id):
    # get ids of elements hosted on element
    elems = DB.FilteredElementCollector(revit.doc).OfClass(DB.FamilyInstance).ToElements()
    hosted_element_ids = [e.Id for e in elems if e.get_Parameter(DB.BuiltInParameter.HOST_ID_PARAM).AsValueString() == str(host_id)]

    return hosted_element_ids


def get_sketch_elements(edited_wall):
    # delete the element and roll back, while catching the IDs of deleted elements
    t1 = DB.Transaction(revit.doc, "temp delete elements")
    t1.Start()
    all_ids = revit.doc.Delete(wall.Id)
    t1.RollBack()

    profile = None
    curves = []
    # pick only sketch elements
    for id in all_ids:
        el = revit.doc.GetElement(id)
        if isinstance(el, DB.Sketch):
            profile = el.Profile
    # formatting: iterate through sketch curve arrays and gather curves
    if not profile:
        return
    else:
        for curve_arr in profile:
            for curve in curve_arr:
                curves.append(curve)
        return List[DB.Curve](curves)


# format wall types dict for ui window
coll_wt = DB.FilteredElementCollector(revit.doc).OfClass(DB.WallType)
filtered_types = [wt for wt in coll_wt if wt.Kind == DB.WallKind.Basic]
wall_type_dict = {ft.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString() : ft for ft in filtered_types}

# format document phases dict for ui window
doc_phases_dict = {ph.Name : ph for ph in revit.doc.Phases}

# rwp UI: pick wall type and phase
components = [Label("Select Wall Type:"),
              ComboBox("combobox1", wall_type_dict),
              Label("Select Phase:"),
              ComboBox("combobox2", doc_phases_dict),
              Separator(),
              Button("Select")]
form = FlexForm("Settings", components)
form.show()
chosen_wall_type = form.values["combobox1"]
chosen_phase = form.values["combobox2"]

# collect walls in project that are Basic walls and not in Insulation Phase
coll_all_walls = DB.FilteredElementCollector(revit.doc) \
    .OfClass(DB.Wall) \
    .WhereElementIsNotElementType() \
    .ToElements()

ins_walls = [w for w in coll_all_walls if w.WallType.Kind == DB.WallKind.Basic
             and wall_type_has_ins(w.WallType)
             and w.get_Parameter(DB.BuiltInParameter.PHASE_CREATED) != chosen_phase]

# for each list of walls of one wall type
for wall in ins_walls:

    # width of insulation layer
    ins_layer_width = get_ins_layer_width(wall.WallType)

    # calculate the position of the ins layer for later
    ins_position = get_ins_position(wall.WallType)
    position = (ins_position + ins_layer_width/2)-(wall.WallType.Width / 2)

    # iterate trough walls and create a new wall for each one

    # if wall has edited profile, get the sketch elements
    profile = get_sketch_elements(wall)

    # create new wall
    with revit.Transaction("Create new wall", revit.doc):

        # get the parameters of the original wall
        height = wall.get_Parameter(DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM).AsDouble()
        level_offset = wall.get_Parameter(DB.BuiltInParameter.WALL_BASE_OFFSET).AsDouble()
        flipped = wall.Flipped
        structural = wall.get_Parameter(DB.BuiltInParameter.WALL_STRUCTURAL_SIGNIFICANT).AsValueString()

        if profile: # if wall has edited profile, recreate profile
            # create new wall by profile, wall type, level, structural
            new_wall = DB.Wall.Create(revit.doc, profile, chosen_wall_type.Id, wall.LevelId, structural)
            print ("created wall id", new_wall.Id)

        # if wall is attached, read its geometry and represent it with a profile
        elif wall.get_Parameter(DB.BuiltInParameter.WALL_TOP_IS_ATTACHED).AsInteger() == 1 \
                or wall.get_Parameter(DB.BuiltInParameter.WALL_BOTTOM_IS_ATTACHED).AsInteger() == 1:
            # get side faces as reference
            reference_face = DB.HostObjectUtils.GetSideFaces(wall, DB.ShellLayerType.Exterior)
            # access side face from reference
            side_face = revit.doc.GetElement(reference_face[0]).GetGeometryObjectFromReference(reference_face[0])
            # get the outer loop of edges by comparing accumulative lengths of edges
            outer_loop = None
            max_length = 0.0
            for edge_array in side_face.EdgeLoops:  # edge array array
                length = 0.0
                for edge in edge_array:
                    length += edge.AsCurve().Length
                if length > max_length:
                    max_length = length
                    outer_loop = [edge.AsCurve() for edge in edge_array]
            attached_profile = List[DB.Curve](outer_loop)  # format curve loop as IList
            new_wall = DB.Wall.Create(revit.doc, attached_profile, chosen_wall_type.Id, wall.LevelId, structural)
        else:
            # if not, just create the wall
            new_wall = DB.Wall.Create(revit.doc, wall.Location.Curve, chosen_wall_type.Id, wall.LevelId, height, level_offset, flipped, structural)

        # move to phase
        new_wall.CreatedPhaseId = chosen_phase.Id
        new_wall.DemolishedPhaseId = chosen_phase.Id

        # offset wall using calculated position
        new_wall_location_curve = new_wall.Location.Curve
        # correct normal direction if wall is flipped
        if flipped:
            new_wall_location_curve = new_wall_location_curve.CreateReversed()
        e1 = new_wall_location_curve.GetEndPoint(0)
        e2 = new_wall_location_curve.GetEndPoint(1)
        h = DB.XYZ(e1.X, e1.Y, 5)
        centerline_plane = DB.Plane.CreateByThreePoints(e1, e2, h)
        # offset curve by some distance
        vector = centerline_plane.Normal * position
        move = new_wall.Location.Move(vector)