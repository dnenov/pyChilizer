__title__ = "Room Data Sheets"
__doc__ = "Creates room plans and elevations and places them on a sheet. Assign sheet number and view templates. The " \
          "view plans will be rotates along the room's longest boundary. If room boundary allows, it will be offset " \
          "to include the walls. "

from pyrevit import revit, DB, script, forms, HOST_APP
from rpw.ui.forms import FlexForm, Label, TextBox, Button,ComboBox, Separator
import helper
from pyrevit.revit.db import query
from itertools import izip
from collections import namedtuple
import math
from Autodesk.Revit import Exceptions
from pyrevit.framework import List
import re

output = script.get_output()
logger = script.get_logger()
bound_opt = DB.SpatialElementBoundaryOptions()
# use preselected elements, filtering rooms only
selection = helper.select_rooms_filter()
if not selection:
    forms.alert("You need to select at least one Room.", exitscript=True)

# DONE: choose longest curve to rotate by, also if it's a line
# DONE: try using room boundaries for crop, if fails use BBox
# TODO: try using room boundaries for crop, if fails use BBox, correct the bbox rotation on fail
# DONE: assign templates - done
# DONE: offset boundary curve - done
# DONE: ask for scale and sheet number
# DONE: add indexes ABCD
# DONE: ask for settings
# Done: Offest elevation crop
# Done: place by crop not by bounding box
# TODO: move all functions to helper
# Done: debug characters


def solidify_bbox(bbox):
    bottom_z_offset = 0.1
    solid_opt = DB.SolidOptions(DB.ElementId.InvalidElementId, DB.ElementId.InvalidElementId)
    bbox.Min = DB.XYZ(bbox.Min.X, bbox.Min.Y, bbox.Min.Z - bottom_z_offset)
    b1 = DB.XYZ(bbox.Min.X, bbox.Min.Y, bbox.Min.Z)
    b2 = DB.XYZ(bbox.Max.X, bbox.Min.Y, bbox.Min.Z)
    b3 = DB.XYZ(bbox.Max.X, bbox.Max.Y, bbox.Min.Z)
    b4 = DB.XYZ(bbox.Min.X, bbox.Max.Y, bbox.Min.Z)
    bbox_height = bbox.Max.Z - bbox.Min.Z

    lines = List[DB.Curve]()
    lines.Add(DB.Line.CreateBound(b1, b2))
    lines.Add(DB.Line.CreateBound(b2, b3))
    lines.Add(DB.Line.CreateBound(b3, b4))
    lines.Add(DB.Line.CreateBound(b4, b1))
    rectangle = [DB.CurveLoop.Create(lines)]

    extrusion = DB.GeometryCreationUtilities.CreateExtrusionGeometry(List[DB.CurveLoop](rectangle),
                                                                     DB.XYZ.BasisZ,
                                                                     bbox_height,
                                                                     solid_opt)

    category_id = DB.ElementId(DB.BuiltInCategory.OST_GenericModel)
    direct_shape = DB.DirectShape.CreateElement(revit.doc, category_id)
    direct_shape.SetShape([extrusion])
    return direct_shape


def geo_to_ds(geo):
    category_id = DB.ElementId(DB.BuiltInCategory.OST_GenericModel)
    direct_shape = DB.DirectShape.CreateElement(revit.doc, category_id)
    direct_shape.SetShape([geo])
    return direct_shape


def get_bb_outline(bb):

    r1 = DB.XYZ(bb.Min.X, bb.Min.Y, bb.Min.Z)
    r2 = DB.XYZ(bb.Max.X, bb.Min.Y, bb.Min.Z)
    r3 = DB.XYZ(bb.Max.X, bb.Max.Y, bb.Min.Z)
    r4 = DB.XYZ(bb.Min.X, bb.Max.Y, bb.Min.Z)

    l1 = DB.Line.CreateBound(r1, r2)
    l2 = DB.Line.CreateBound(r2, r3)
    l3 = DB.Line.CreateBound(r3, r4)
    l4 = DB.Line.CreateBound(r4, r1)

    curves_set = [l1, l2, l3, l4]
    return curves_set


def apply_vt(v, vt):
    if vt:
        v.ViewTemplateId = vt.Id
    return


def get_aligned_crop(geo, transform):

    rotated_geo = geo.GetTransformed(transform)
    revit.doc.Regenerate()
    rb = rotated_geo.GetBoundingBox()
    bb_outline = get_bb_outline(rb)
    # rotate the curves back using the opposite direction
    tr_back = transform.Inverse
    rotate_curves_back = [c.CreateTransformed(tr_back) for c in bb_outline]
    crop_loop = DB.CurveLoop.Create(List[DB.Curve](rotate_curves_back))

    return crop_loop


def is_metric(doc):
    display_units = DB.Document.GetUnits(doc).GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
    metric_units = [
        DB.DisplayUnitType.DUT_METERS,
        DB.DisplayUnitType.DUT_CENTIMETERS,
        DB.DisplayUnitType.DUT_DECIMETERS,
        DB.DisplayUnitType.DUT_MILLIMETERS,
        DB.DisplayUnitType.DUT_METERS_CENTIMETERS
    ]
    if display_units in set(metric_units):
        return True
    else:
        return False


# collect all view templates for plans and sections
viewsections = DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewSection) # collect sections
viewsection_dict = {v.Name: v for v in viewsections if v.IsTemplate} # only fetch the IsTemplate sections

viewplans = DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewPlan) # collect plans
viewplan_dict = {v.Name: v for v in viewplans if v.IsTemplate} # only fetch IsTemplate plans
# add none as an option
viewplan_dict["<None>"] = None
viewsection_dict["<None>"] = None

# collect titleblocks in a dictionary
titleblocks = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType()
tblock_dict = {'{}: {}'.format(tb.FamilyName, revit.query.get_name(tb)): tb for tb in titleblocks}

# collect and take the first view plan type, elevation type, set default scale
col_view_types = (DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType).WhereElementIsElementType())
floor_plan_type = [vt for vt in col_view_types if vt.FamilyName == "Floor Plan"][0]
# plan_type = DB.ViewType.FloorPlan
elevation_type = [vt for vt in DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType) if vt.FamilyName == "Elevation"][0]
view_scale = 50

# get units for Crop Offset variable
display_units = DB.Document.GetUnits(revit.doc).GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
if is_metric(revit.doc):
    unit_sym = "Crop Offset [mm]"
    default_crop_offset = 350
else:
    unit_sym = "Crop Offset [decimal inches]"
    default_crop_offset = 9.0

components = [
    Label ("Select Titleblock"),
    ComboBox(name="tb", options=sorted(tblock_dict)),
    Label("Sheet Number"),
    TextBox("sheet_number", Text="1000"),
    Label(unit_sym),
    TextBox("crop_offset", Text=str(default_crop_offset)),
    Label("View Template for Plans"),
    ComboBox(name="vt_plans", options=sorted(viewplan_dict), default="<None>"),
    Label("View Template for Elevations"),
    ComboBox(name="vt_elevs", options=sorted(viewsection_dict), default="<None>"),
    Separator(),
    Button("Select"),
]


def correct_input_units(val):
    import re
    try:
        digits = float(val)
    except ValueError:
        # format the string using regex
        digits = re.findall("[0-9.]+", val)[0]
    if is_metric(revit.doc):
        return DB.UnitUtils.ConvertToInternalUnits(float(digits), DB.DisplayUnitType.DUT_MILLIMETERS)
    else:
        return DB.UnitUtils.ConvertToInternalUnits(float(digits), DB.DisplayUnitType.DUT_DECIMAL_INCHES)


form = FlexForm("Set Sheet Number", components)
form.show()
# match the variables with user input
chosen_sheet_nr = form.values["sheet_number"]
chosen_vt_plan = viewplan_dict[form.values["vt_plans"]]
chosen_vt_elevation = viewsection_dict[form.values["vt_elevs"]]
chosen_tb = tblock_dict[form.values["tb"]]
chosen_crop_offset = correct_input_units(form.values["crop_offset"])

# approximate positions for viewports on an A1 sheet
plan_position = DB.XYZ(0.282, 0.434, 0)
elevations_positions = [
    DB.XYZ(1.14, 1.25, 0),
    DB.XYZ(1.805, 1.25, 0),
    DB.XYZ(1.14, 0.434, 0),
    DB.XYZ(1.805, 0.434, 0),
]

for room in selection:
    with revit.Transaction("Create Plan", revit.doc):
        level = room.Level
        room_location = room.Location.Point
        # Create Floor Plan
        viewplan = DB.ViewPlan.Create(revit.doc, floor_plan_type.Id, level.Id)
        viewplan.Scale = view_scale

    # find crop box element (method with transactions, must be outside transaction)
    crop_box_el = helper.find_crop_box(viewplan)

    with revit.Transaction("Create Elevations", revit.doc):
        # rotate the view plan along the room's longest boundary
        axis = helper.get_bb_axis_in_view(room, viewplan)
        angle = helper.room_rotation_angle(room)
        rotated = DB.ElementTransformUtils.RotateElement(
            revit.doc, crop_box_el.Id, axis, angle
        )
        viewplan.CropBoxActive = True
        revit.doc.Regenerate()

        room_boundaries = helper.get_room_bound(room)
        if room_boundaries:
            # try offsetting boundaries (to include walls in plan view)
            try:
                offset_boundaries = room_boundaries.CreateViaOffset(
                    room_boundaries, chosen_crop_offset, DB.XYZ(0, 0, 1)
                )
                crop_shape = viewplan.GetCropRegionShapeManager()
                crop_shape.SetCropShape(offset_boundaries)
                revit.doc.Regenerate()
            # for some shapes the offset will fail, then use BBox method
            except:
                revit.doc.Regenerate()
                # room bbox in this view
                new_bbox = room.get_BoundingBox(viewplan)
                viewplan.CropBox = new_bbox
                solidify_bbox(new_bbox)
                # this part corrects the rotation of the BBox

                tr_left = DB.Transform
                tr_left = tr_left.CreateRotationAtPoint(DB.XYZ.BasisZ, angle, room_location)


                tr_right = DB.Transform
                tr_right = tr_right.CreateRotationAtPoint(DB.XYZ.BasisZ, -angle, room_location)

                rotate_left = get_aligned_crop(room.ClosedShell, tr_left)
                rotate_right = get_aligned_crop(room.ClosedShell, tr_right)

                # len1 = rotate_left.GetExactLength()
                # len2 = rotate_right.GetExactLength()
                # print ("L {}, R {}".format(len1, len2))
                # aligned_crop_loop = None
                # if len1 < len2:
                #     print ("Rotate Left")
                #     aligned_crop_loop = rotate_left
                # else:
                #     print ("Rotate Right")
                #     aligned_crop_loop = rotate_right
                aligned_crop_loop = rotate_right
                crsm = viewplan.GetCropRegionShapeManager()
                curve_loop_offset = DB.CurveLoop.CreateViaOffset(aligned_crop_loop, chosen_crop_offset, DB.XYZ.BasisZ)
                crsm.SetCropShape(aligned_crop_loop)

        # Rename Floor Plan
        room_name_nr = (
                room.Number
                + " - "
                + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        )
        viewplan_name = room_name_nr + " Plan"
        while helper.get_view(viewplan_name):
            viewplan_name = viewplan_name + " Copy 1"
        viewplan.Name = viewplan_name
        helper.set_anno_crop(viewplan)

        # Create Elevations
        revit.doc.Regenerate()
        elevations_col = []
        new_marker = DB.ElevationMarker.CreateElevationMarker(
            revit.doc, elevation_type.Id, room_location, view_scale
        )
        elevation_count = ["A", "B", "C", "D"]
        revit.doc.Regenerate()
        for i in range(4):
            elevation = new_marker.CreateElevation(revit.doc, viewplan.Id, i)
            elevation.Scale = view_scale
            # Rename elevations
            elevation_name = room_name_nr + " - Elevation " + elevation_count[i]
            while helper.get_view(elevation_name):
                elevation_name = elevation_name + " Copy 1"

            elevation.Name = elevation_name
            elevations_col.append(elevation)
            helper.set_anno_crop(elevation)

        # rotate marker
        revit.doc.Regenerate()
        marker_axis = DB.Line.CreateBound(
            room_location, room_location + DB.XYZ.BasisZ
        )
        rotated = new_marker.Location.Rotate(marker_axis, angle)
        revit.doc.Regenerate()

        sheet = helper.create_sheet(chosen_sheet_nr, room_name_nr, chosen_tb.Id)

    with revit.Transaction("Add Views to Sheet", revit.doc):
        # apply view template
        apply_vt(viewplan, chosen_vt_plan)
        # place view on sheet
        place_plan = DB.Viewport.Create(revit.doc, sheet.Id, viewplan.Id, plan_position)
        # correct the position, taking Viewport Box Outline as reference
        delta_pl = plan_position - place_plan.GetBoxOutline().MinimumPoint
        move_pl = DB.ElementTransformUtils.MoveElement(
            revit.doc, place_plan.Id, delta_pl
        )
        for el, pos, i in izip(elevations_col, elevations_positions, elevation_count):
            # place elevations
            place_elevation = DB.Viewport.Create(revit.doc, sheet.Id, el.Id, pos)
            # set viewport detail number
            place_elevation.get_Parameter(
                DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER
            ).Set(i)
            # correct the positions
            delta_el = pos - place_elevation.GetBoxOutline().MinimumPoint
            move_el = DB.ElementTransformUtils.MoveElement(
                revit.doc, place_elevation.Id, delta_el
            )
            revit.doc.Regenerate()
            room_bb = room.get_BoundingBox(el)
            helper.set_crop_to_bb(room, el, crop_offset=chosen_crop_offset)
            apply_vt(el, chosen_vt_elevation)

        revit.doc.Regenerate()


        print("Sheet : {0} \t Room {1} ".format(output.linkify(sheet.Id), room_name_nr))
