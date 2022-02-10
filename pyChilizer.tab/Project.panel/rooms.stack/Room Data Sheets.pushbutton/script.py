__title__ = "Room Data Sheets"
__doc__ = "Creates room plans and elevations and places them on a sheet. Assign sheet number and view templates. The " \
          "view plans will be rotates along the room's longest boundary. If room boundary allows, it will be offset " \
          "to include the walls. "

from pyrevit import revit, DB, script, forms, HOST_APP
from rpw.ui.forms import FlexForm, Label, TextBox, Button, ComboBox, CheckBox, Separator
import locator
from itertools import izip
import sys
from pychilizer import units, select, geo, database

output = script.get_output()
logger = script.get_logger()    #helps to debug script, not used

selection = select.select_rooms_filter()
if not selection:
    forms.alert("You need to select at least one Room.", exitscript=True)

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
tblock_orientation = ['Vertical', 'Horizontal']
layout_orientation = ['Tiles', 'Cross']

# collect and take the first view plan type, elevation type, set default scale
floor_plan_type = database.get_view_family_types(DB.ViewFamily.FloorPlan)[0]
ceiling_plan_type = database.get_view_family_types(DB.ViewFamily.CeilingPlan)[0]
elevation_type = database.get_view_family_types(DB.ViewFamily.Elevation)[0]
view_scale = 50

# get units for Crop Offset variable
if units.is_metric(revit.doc):
    unit_sym = "Crop Offset [mm]"
    default_crop_offset = 350
else:
    unit_sym = "Crop Offset [decimal inches]"
    default_crop_offset = 9.0

# get units for Crop Offset variable
if units.is_metric(revit.doc):
    tb_offset = 165
else:
    tb_offset = 4.2

components = [
    Label ("Select Titleblock"),
    ComboBox(name="tb", options=sorted(tblock_dict)),
    Label("Sheet Number"),
    TextBox("sheet_number", Text="1000"),
    Label(unit_sym),
    TextBox("crop_offset", Text=str(default_crop_offset)),
    Label("Titleblock (internal) offset"),
    TextBox("titleblock_offset", Text=str(tb_offset)),
    Label("Layout orientation"),
    ComboBox(name="layout_orientation", options=layout_orientation, default="Tiles"),
    CheckBox("el_rotation", 'Rotate elevations', default=False),
    Label("Titleblock orientation"),
    ComboBox(name="tb_orientation", options=tblock_orientation, default="Vertical"),
    Separator(),
    Label("View Template for Plans"),
    ComboBox(name="vt_plans", options=sorted(viewplan_dict), default="<None>"),
    Label("View Template for Reflected Ceiling Plans"),
    ComboBox(name="vt_rcp_plans", options=sorted(viewplan_dict), default="<None>"),
    Label("View Template for Elevations"),
    ComboBox(name="vt_elevs", options=sorted(viewsection_dict), default="<None>"),
    Separator(),
    Button("Select"),
]

form = FlexForm("Set Sheet Number", components)
ok = form.show()

if ok:
    # match the variables with user input
    chosen_sheet_nr = form.values["sheet_number"]
    chosen_vt_plan = viewplan_dict[form.values["vt_plans"]]
    chosen_vt_rcp_plan = viewplan_dict[form.values["vt_rcp_plans"]]
    chosen_vt_elevation = viewsection_dict[form.values["vt_elevs"]]
    chosen_tb = tblock_dict[form.values["tb"]]
    chosen_crop_offset = units.correct_input_units(form.values["crop_offset"])
    titleblock_offset = units.correct_input_units(form.values["titleblock_offset"])
    layout_ori = form.values["layout_orientation"]
    tb_ori = form.values["tb_orientation"]
    elev_rotate = form.values["el_rotation"]
else:
    sys.exit()

for room in selection:
    with revit.Transaction("Create Plan", revit.doc):
        level = room.Level
        room_location = room.Location.Point

        # Create Floor Plan
        viewplan = DB.ViewPlan.Create(revit.doc, floor_plan_type.Id, level.Id)
        viewplan.Scale = view_scale

        # Create Reflected Ceilign Plan
        viewRCP = DB.ViewPlan.Create(revit.doc, ceiling_plan_type.Id, level.Id)
        viewRCP.Scale = view_scale

    # find crop box element (method with transactions, must be outside transaction)
    crop_box_plan = geo.find_crop_box(viewplan)
    crop_box_rcp = geo.find_crop_box(viewRCP)

    with revit.Transaction("Crop and Create Elevations", revit.doc):
        # rotate the view plan along the room's longest boundary
        axis = geo.get_bb_axis_in_view(room, viewplan)

        angle = geo.room_rotation_angle(room)

        rotated_plan = DB.ElementTransformUtils.RotateElement(
            revit.doc, crop_box_plan.Id, axis, angle
        )

        rotated_rcp = DB.ElementTransformUtils.RotateElement(
            revit.doc, crop_box_rcp.Id, axis, angle
        )

        viewplan.CropBoxActive = True
        viewRCP.CropBoxActive = True
        revit.doc.Regenerate()

        room_boundaries = geo.get_room_bound(room)
        if room_boundaries:
            # try offsetting boundaries (to include walls in plan view)
            try:
                offset_boundaries = room_boundaries.CreateViaOffset(
                    room_boundaries, chosen_crop_offset, DB.XYZ(0, 0, 1)
                )
                crop_shape = viewplan.GetCropRegionShapeManager()
                crop_shape.SetCropShape(offset_boundaries)
                crop_RCP = viewRCP.GetCropRegionShapeManager()
                crop_RCP.SetCropShape(offset_boundaries)
                revit.doc.Regenerate()
            # for some shapes the offset is not obvious and will fail, then use BBox method:
            except:
                revit.doc.Regenerate()
                # using a helper method, get the outlines of the room's bounding box,
                # then rotate them with an already known angle (inverted)
                rotation = DB.Transform.CreateRotationAtPoint(DB.XYZ.BasisZ, angle, room_location)
                rotated_crop_loop = geo.get_aligned_crop(room.ClosedShell, rotation.Inverse)

                # offset the curve loop with given offset
                # set the loop as Crop Shape of the view using CropRegionShapeManager
                crsm = viewplan.GetCropRegionShapeManager()
                crsm_rcp = viewRCP.GetCropRegionShapeManager()
                curve_loop_offset = DB.CurveLoop.CreateViaOffset(rotated_crop_loop, chosen_crop_offset, DB.XYZ.BasisZ)
                crsm.SetCropShape(curve_loop_offset)
                crsm_rcp.SetCropShape(curve_loop_offset)

        # Rename Floor Plan
        room_name_nr = (
                room.Number
                + " - "
                + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        )
        viewplan_name = room_name_nr + " Plan"
        while database.get_view(viewplan_name):
            viewplan_name = viewplan_name + " Copy 1"
        viewplan.Name = viewplan_name
        database.set_anno_crop(viewplan)

        # Rename Reflected Ceiling Plan
        RCP_name = room_name_nr + "Reflected Ceiling Plan"
        while database.get_view(RCP_name):
            RCP_name = RCP_name + " Copy 1"
        viewRCP.Name = RCP_name
        database.set_anno_crop(viewRCP)

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
            while database.get_view(elevation_name):
                elevation_name = elevation_name + " Copy 1"

            elevation.Name = elevation_name
            elevations_col.append(elevation)
            database.set_anno_crop(elevation)

        # rotate marker
        revit.doc.Regenerate()
        marker_axis = DB.Line.CreateBound(
            room_location, room_location + DB.XYZ.BasisZ
        )
        rotated = new_marker.Location.Rotate(marker_axis, angle)
        revit.doc.Regenerate()
        sheet = database.create_sheet(chosen_sheet_nr, room_name_nr, chosen_tb.Id)
    
    # get positions on sheet
    loc = locator.Locator(sheet, titleblock_offset, tb_ori, layout_ori)
    plan_position = loc.plan
    RCP_position = loc.rcp
    elevations_positions = loc.elevations 

    elevations = [] # collect all elevations we create
    
    with revit.Transaction("Add Views to Sheet", revit.doc):
        # apply view template
        database.apply_vt(viewplan, chosen_vt_plan)
        database.apply_vt(viewRCP, chosen_vt_rcp_plan)

        # place view on sheet
        place_plan = DB.Viewport.Create(revit.doc, sheet.Id, viewplan.Id, plan_position)
        place_RCP = DB.Viewport.Create(revit.doc, sheet.Id, viewRCP.Id, RCP_position)
        
        for el, pos, i in izip(elevations_col, elevations_positions, elevation_count):
            # place elevations
            place_elevation = DB.Viewport.Create(revit.doc, sheet.Id, el.Id, pos)

            # if user selected, rotate elevations
            if elev_rotate and i == "A":
                place_elevation.Rotation = DB.ViewportRotation.Counterclockwise
            if elev_rotate and i == "C":
                place_elevation.Rotation = DB.ViewportRotation.Clockwise    

            # set viewport detail number
            place_elevation.get_Parameter(
                DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER
            ).Set(i)
            elevations.append(place_elevation)
            revit.doc.Regenerate()
            room_bb = room.get_BoundingBox(el)
            geo.set_crop_to_bb(room, el, crop_offset=chosen_crop_offset)
            database.apply_vt(el, chosen_vt_elevation)

        revit.doc.Regenerate()
        
        # realign the viewports to their desired positions
        loc.realign_pos(revit.doc, [place_plan], [plan_position])
        loc.realign_pos(revit.doc, [place_RCP], [RCP_position])
        loc.realign_pos(revit.doc, elevations, elevations_positions)

        print("Sheet : {0} \t Room {1} ".format(output.linkify(sheet.Id), room_name_nr))
