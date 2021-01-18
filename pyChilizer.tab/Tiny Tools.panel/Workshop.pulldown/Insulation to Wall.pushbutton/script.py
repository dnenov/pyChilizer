__title__ = "Insulation\nto Wall"
__doc__ = "Creates a new wall representing the insulation layer"

from pyrevit import revit, DB, script, forms
from pyrevit.framework import List
import math

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
            # TODO: if clause for more than one ins layer
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


def find_ins_wall(width):
    # which parameter to look at
    parameter_value_provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.WALL_ATTR_WIDTH_PARAM))
    # construct filter rule
    width_rule = DB.FilterDoubleRule(parameter_value_provider, DB.FilterNumericEquals(), width, 10e-10)
    # using slow parameter filter
    width_filter = DB.ElementParameterFilter(width_rule)
    # filter wall types of same width as insulation layer
    width_wall_types = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_Walls) \
        .WhereElementIsElementType() \
        .WherePasses(width_filter) \
        .ToElements()
    # iterate through wall types to find one that have one layer of insulation
    for wt in width_wall_types:
        compound_str = wt.GetCompoundStructure()
        num = compound_str.LayerCount
        if num == 1 and str(compound_str.GetLayerFunction(0)) == "Insulation":
            return wt


def group_by_key(items_list, keys):
    # group list by keys
    unique_keys = set(keys)
    results = []
    for unique_item in unique_keys:
        key_group = []
        for element, key in zip(items_list, keys):
            if key == unique_item:
                key_group.append(element)
        results.append(key_group)
    return results


def get_sketch_elements (wall):
    # delete the element and roll back, while catching the IDs of deleted elements
    t1 = DB.Transaction(revit.doc, "del el")
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
    for curve_arr in profile:
        for curve in curve_arr:
            curves.append(curve)
    return List[DB.Curve](curves)



# Pick material to set to new walls:
materials = DB.FilteredElementCollector(revit.doc).OfClass(DB.Material).ToElements()
chosen_mat = None

# TODO: Pick materials from list or pick default wall material
# pick one to illustrate
for mat in materials:
    if mat.Name == "Default Mass Exterior Wall":
        chosen_mat = mat

# pick a phase to move new objects to
phases = DB.FilteredElementCollector(revit.doc).OfClass(DB.Phase)
ins_phase = [ph for ph in phases if ph.Name == "Insulation"]


# collect walls in project
coll_all_walls = DB.FilteredElementCollector(revit.doc) \
    .OfClass(DB.Wall) \
    .WhereElementIsNotElementType() \
    .ToElements()
ins_walls = []
for w in coll_all_walls:
    if w.WallType.Kind == DB.WallKind.Basic and wall_type_has_ins(w.WallType) and w.get_Parameter(DB.BuiltInParameter.PHASE_CREATED)!= ins_phase:
        ins_walls.append(w)

# sort walls and wall types
wall_dict = {}
for wall in ins_walls:
    wall_dict[wall] = wall.WallType
# group walls by type
walls_by_type = group_by_key(wall_dict.keys(), wall_dict.values())

# for each list of walls of one wall type
for wall_group in walls_by_type:
    insulation_wall_type = None
    # wall type of each wall group
    wall_type = wall_group[0].WallType
    # width of insulation layer
    ins_layer_width = get_ins_layer_width(wall_type)
    # if wall with same width and ins layer exists already, use it
    insulation_wall_type = find_ins_wall(ins_layer_width)
    if not insulation_wall_type:
        # if not - create a new type by duplicating
        with revit.Transaction("Create wall type", revit.doc):
            # duplicate the wall type and name it
            new_wall_type = wall_type.Duplicate("Insulation Layer " + str(convert_units(ins_layer_width))+"mm")
            # assign function to the layer
            mat_func = DB.MaterialFunctionAssignment.Insulation
            # create compound layer structure
            new_comp_str = DB.CompoundStructure.CreateSingleLayerCompoundStructure(mat_func, ins_layer_width, chosen_mat.Id)
            # set the compound structure to the new wall type
            set_new = new_wall_type.SetCompoundStructure(new_comp_str)
            insulation_wall_type = new_wall_type
            revit.doc.Regenerate()
    # calculate the position of the ins layer for later
    ins_position = get_ins_position(wall_type)
    position = (ins_position + ins_layer_width/2)-(wall_type.Width / 2)
    # iterate trough walls and copy/paste each one
    for wall in wall_group:
        # get the edited profile
        profile = get_sketch_elements(wall)

        # create new wall copying an existing wall
        with revit.Transaction("Create new wall", revit.doc):
            # get the parameters of the original wall
            height = wall.get_Parameter(DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM).AsDouble()
            level_offset = wall.get_Parameter(DB.BuiltInParameter.WALL_BASE_OFFSET).AsDouble()
            flipped = wall.Flipped
            structural = wall.get_Parameter(DB.BuiltInParameter.WALL_STRUCTURAL_SIGNIFICANT).AsValueString()

            # create new wall
            new_wall = DB.Wall.Create(revit.doc, profile, insulation_wall_type.Id, wall.LevelId, structural)
        # move to phase
            new_wall.CreatedPhaseId = ins_phase[0].Id
            new_wall.DemolishedPhaseId = ins_phase[0].Id
        # offset using calculated position
            new_wall_location_curve = new_wall.Location.Curve
            if flipped:
                new_wall_location_curve = new_wall_location_curve.CreateReversed()
            e1 = new_wall_location_curve.GetEndPoint(0)
            e2 = new_wall_location_curve.GetEndPoint(1)
            h = DB.XYZ(e1.X, e1.Y, 5)
            centerline_plane = DB.Plane.CreateByThreePoints(e1, e2, h)
            # offset curve by some distance
            vector = centerline_plane.Normal * position
            move = new_wall.Location.Move(vector)






