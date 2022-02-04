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
logger = script.get_logger()    #helps to debug script, not used
bound_opt = DB.SpatialElementBoundaryOptions()  #not used?

# use preselected elements, filtering rooms only
selection = helper.select_rooms_filter()
if not selection:
    forms.alert("You need to select at least one Room.", exitscript=True)

# TODO: try using room boundaries for crop, if fails use BBox, correct the bbox rotation on fail
# TODO: move all functions to helper

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
tblock_orientation = ['Vertical', 'Horizontal', 'Portrait']

# collect and take the first view plan type, elevation type, set default scale
col_view_types = (DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType).WhereElementIsElementType())
floor_plan_type = [vt for vt in col_view_types if vt.FamilyName == "Floor Plan"][0]
elevation_type = [vt for vt in DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType) if vt.FamilyName == "Elevation"][0]
view_scale = 50

# get units for Crop Offset variable
if helper.is_metric(revit.doc):
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
    Label("Titleblock orientation"),
    ComboBox(name="tb_orientation", options=tblock_orientation, default="Vertical"),
    Separator(),
    Button("Select"),
]

form = FlexForm("Set Sheet Number", components)
form.show()

# TODO: Catch if user cancelled the form

# match the variables with user input
chosen_sheet_nr = form.values["sheet_number"]
chosen_vt_plan = viewplan_dict[form.values["vt_plans"]]
chosen_vt_elevation = viewsection_dict[form.values["vt_elevs"]]
chosen_tb = tblock_dict[form.values["tb"]]
chosen_crop_offset = helper.correct_input_units(form.values["crop_offset"])

# TODO: LAYOUTING OPTIONS

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
                # this part corrects the rotation of the BBox

                tr_left = DB.Transform.CreateRotationAtPoint(DB.XYZ.BasisZ, angle, room_location)
                # tr_right = DB.Transform.CreateRotationAtPoint(DB.XYZ.BasisZ, -angle, room_location)
                tr_right = tr_left.Inverse

                rotate_left = helper.get_aligned_crop(room.ClosedShell, tr_left)
                rotate_right = helper.get_aligned_crop(room.ClosedShell, tr_right)

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


    
    # get positions on sheet
    poss = helper.get_sheet_pos(sheet, chosen_crop_offset, 4, 3)
    plan_position = poss[4]
    elevations_positions = [poss[0], poss[2], poss[6], poss[8]] # a bit hard coded and not pretty at the moment

    print("plan pos: {0}".format(str(plan_position)))

    with revit.Transaction("Add Views to Sheet", revit.doc):
        # apply view template
        helper.apply_vt(viewplan, chosen_vt_plan)
        # place view on sheet
        place_plan = DB.Viewport.Create(revit.doc, sheet.Id, viewplan.Id, plan_position)
        # # correct the position, taking Viewport Box Outline as reference
        # delta_pl = plan_position - place_plan.GetBoxOutline().MinimumPoint
        # move_pl = DB.ElementTransformUtils.MoveElement(
        #     revit.doc, place_plan.Id, delta_pl
        # )
        for el, pos, i in izip(elevations_col, elevations_positions, elevation_count):
            # place elevations
            place_elevation = DB.Viewport.Create(revit.doc, sheet.Id, el.Id, pos)
            # set viewport detail number
            place_elevation.get_Parameter(
                DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER
            ).Set(i)
            # # correct the positions
            # delta_el = pos - place_elevation.GetBoxOutline().MinimumPoint
            # move_el = DB.ElementTransformUtils.MoveElement(
            #     revit.doc, place_elevation.Id, delta_el
            # )
            revit.doc.Regenerate()
            room_bb = room.get_BoundingBox(el)
            helper.set_crop_to_bb(room, el, crop_offset=chosen_crop_offset)
            helper.apply_vt(el, chosen_vt_elevation)

        revit.doc.Regenerate()


    # with revit.Transaction("Add Views to Sheet", revit.doc):
    #     # apply view template
    #     helper.apply_vt(viewplan, chosen_vt_plan)
    #     # place view on sheet
    #     place_plan = DB.Viewport.Create(revit.doc, sheet.Id, viewplan.Id, plan_position)
    #     # correct the position, taking Viewport Box Outline as reference
    #     delta_pl = plan_position - place_plan.GetBoxOutline().MinimumPoint
    #     move_pl = DB.ElementTransformUtils.MoveElement(
    #         revit.doc, place_plan.Id, delta_pl
    #     )
    #     for el, pos, i in izip(elevations_col, elevations_positions, elevation_count):
    #         # place elevations
    #         place_elevation = DB.Viewport.Create(revit.doc, sheet.Id, el.Id, pos)
    #         # set viewport detail number
    #         place_elevation.get_Parameter(
    #             DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER
    #         ).Set(i)
    #         # correct the positions
    #         delta_el = pos - place_elevation.GetBoxOutline().MinimumPoint
    #         move_el = DB.ElementTransformUtils.MoveElement(
    #             revit.doc, place_elevation.Id, delta_el
    #         )
    #         revit.doc.Regenerate()
    #         room_bb = room.get_BoundingBox(el)
    #         helper.set_crop_to_bb(room, el, crop_offset=chosen_crop_offset)
    #         helper.apply_vt(el, chosen_vt_elevation)

    #     revit.doc.Regenerate()


        print("Sheet : {0} \t Room {1} ".format(output.linkify(sheet.Id), room_name_nr))
