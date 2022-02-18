from pyrevit import revit, DB, script
from rpw.ui.forms import FlexForm, Label, TextBox, Button, ComboBox, CheckBox, Separator
import locator, ui
from itertools import izip
import sys
from pychilizer import units, select, geo, database

ui = ui.UI(script)
ui.is_metric = units.is_metric

output = script.get_output()
logger = script.get_logger()  # helps to debug script, not used

selection = select.select_with_cat_filter(DB.BuiltInCategory.OST_Rooms, "Pick Rooms for Room Data Sheets")

# collect all view templates for plans and sections
viewsections = DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewSection)  # collect sections
ui.viewsection_dict = {v.Name: v for v in viewsections if v.IsTemplate}  # only fetch the IsTemplate sections

viewplans = DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewPlan)  # collect plans
ui.viewplan_dict = {v.Name: v for v in viewplans if v.IsTemplate}  # only fetch IsTemplate plans

# TODO
# viewport_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.Viewport).WhereElementIsElementType() # collect all viewport types
# ui.viewport_dict = {v.Name: v for v in viewport_types}  

# add none as an option
ui.viewsection_dict["<None>"] = None
ui.viewplan_dict["<None>"] = None

ui.set_viewtemplates()

# collect titleblocks in a dictionary
titleblocks = DB.FilteredElementCollector(revit.doc).OfCategory(
    DB.BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType()
ui.titleblock_dict = {'{}: {}'.format(tb.FamilyName, revit.query.get_name(tb)): tb for tb in titleblocks}
ui.set_titleblocks()


# collect and take the first view plan type, elevation type, set default scale
floor_plan_type = database.get_view_family_types(DB.ViewFamily.FloorPlan)[0]
# floor_plan_type=[vt for vt in DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType) if
#                 vt.ViewFamily == DB.ViewFamily.FloorPlan][0]
ceiling_plan_type = database.get_view_family_types(DB.ViewFamily.CeilingPlan)[0]
elevation_type = database.get_view_family_types(DB.ViewFamily.Elevation)[0]
section_type = database.get_view_family_types(DB.ViewFamily.Section)[0]

view_scale = 50

# get units for Crop Offset variable
if units.is_metric(revit.doc):
    unit_sym = "Crop Offset [mm]"
else:
    unit_sym = "Crop Offset [decimal inches]"

components = [
    Label("Select Titleblock"),
    ComboBox(name="tb", options=sorted(ui.titleblock_dict), default=database.tb_name_match(ui.titleblock)),
    Label("Sheet Number"),
    TextBox("sheet_number", Text=ui.sheet_number),
    Label(unit_sym),
    TextBox("crop_offset", Text=str(ui.crop_offset)),
    Label("Titleblock (internal) offset"),
    TextBox("titleblock_offset", Text=str(ui.titleblock_offset)),
    Label("Layout orientation"),
    ComboBox(name="layout_orientation", options=ui.layout_orientation, default=ui.layout_ori),
    CheckBox("el_rotation", 'Rotate elevations', default=ui.rotated_elevations),
    CheckBox("el_as_sec", 'Elevations as Sections', default=ui.el_as_sec),
    Label("Titleblock orientation"),
    ComboBox(name="tb_orientation", options=ui.tblock_orientation, default=ui.titleblock_orientation),
    Separator(),
    Label("View Template for Plans"),
    ComboBox(name="vt_plans", options=sorted(ui.viewplan_dict), default=database.vt_name_match(ui.viewplan)),
    Label("View Template for Reflected Ceiling Plans"),
    ComboBox(name="vt_rcp_plans", options=sorted(ui.viewplan_dict), default=database.vt_name_match(ui.viewceiling)),
    Label("View Template for Elevations"),
    ComboBox(name="vt_elevs", options=sorted(ui.viewsection_dict), default=database.vt_name_match(ui.viewsection)),
    # Label("Viewport Type"),
    # ComboBox(name="vp_types", options=sorted(ui.viewport_dict), default=database.vp_name_match(ui.viewport)),
    Separator(),
    Button("Select"),
]

form = FlexForm("Set Sheet Number", components)
ok = form.show()

if ok:
    # match the variables with user input
    chosen_sheet_nr = form.values["sheet_number"]
    chosen_vt_plan = ui.viewplan_dict[form.values["vt_plans"]]
    chosen_vt_rcp_plan = ui.viewplan_dict[form.values["vt_rcp_plans"]]
    chosen_vt_elevation = ui.viewsection_dict[form.values["vt_elevs"]]
    chosen_tb = ui.titleblock_dict[form.values["tb"]]
    chosen_crop_offset = units.correct_input_units(form.values["crop_offset"])
    titleblock_offset = units.correct_input_units(form.values["titleblock_offset"])
    layout_ori = form.values["layout_orientation"]
    tb_ori = form.values["tb_orientation"]
    elev_rotate = form.values["el_rotation"]
    elev_as_sections = form.values["el_as_sec"]
else:
    sys.exit()

ui.set_config("sheet_number", chosen_sheet_nr)
ui.set_config("crop_offset", form.values["crop_offset"])
ui.set_config("titleblock_offset", form.values["titleblock_offset"])
ui.set_config("titleblock_orientation", tb_ori)
ui.set_config("layout_orientation", layout_ori)
ui.set_config("rotated_elevations", elev_rotate)
ui.set_config("el_as_sec", elev_as_sections)
ui.set_config("titleblock", form.values["tb"])
ui.set_config("viewplan", form.values["vt_plans"])
ui.set_config("viewceiling", form.values["vt_rcp_plans"])
ui.set_config("viewsection", form.values["vt_elevs"])

for room in selection:
    with revit.Transaction("Create Plan", revit.doc):
        level = room.Level
        room_location = room.Location.Point

        # Create Floor Plan
        viewplan = DB.ViewPlan.Create(revit.doc, floor_plan_type.Id, level.Id)
        # weird bug happened here, solved re-launching revit
        viewplan.Scale = view_scale

        # Create Reflected Ceiling Plan
        viewRCP = DB.ViewPlan.Create(revit.doc, ceiling_plan_type.Id, level.Id)
        viewRCP.Scale = view_scale

        if layout_ori == "Cross":
            threeD = geo.create_room_axo_rotate(room, view_scale)

    # find crop box element (method with transactions, must be outside transaction)
    crop_box_plan = geo.find_crop_box(viewplan)
    crop_box_rcp = geo.find_crop_box(viewRCP)

    with revit.Transaction("Crop and Create Elevations", revit.doc):
        # rotate the view plan
        axis = geo.get_bb_axis_in_view(room, viewplan)  # get the axis for rotation
        angle = geo.room_rotation_angle(room)  # rotate the room geometry by longest boundary

        # rotate plan
        rotated_plan = DB.ElementTransformUtils.RotateElement(
            revit.doc, crop_box_plan.Id, axis, angle
        )
        # rotate RCP
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
                rotated_crop_loop = geo.room_bb_outlines(room)
                # offset the curve loop with given offset
                curve_loop_offset = DB.CurveLoop.CreateViaOffset(rotated_crop_loop, chosen_crop_offset, DB.XYZ.BasisZ)
                # set the loop as Crop Shape of the view using CropRegionShapeManager
                crsm_plan = viewplan.GetCropRegionShapeManager()
                crsm_rcp = viewRCP.GetCropRegionShapeManager()
                crsm_plan.SetCropShape(curve_loop_offset)
                crsm_rcp.SetCropShape(curve_loop_offset)

        # Construct View Names
        room_name_nr = (
                room.Number
                + " - "
                + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        )

        # rename views
        viewplan.Name = database.unique_view_name(room_name_nr, suffix=" Plan")
        viewRCP.Name = database.unique_view_name(room_name_nr, suffix=" Reflected Ceiling Plan")
        # if created, rename the axo too
        if layout_ori == "Cross":
            threeD.Name = database.unique_view_name(room_name_nr, suffix=" Axo View")
        # activate annotation crop
        database.set_anno_crop(viewplan)
        database.set_anno_crop(viewRCP)

        # Create Elevations
        revit.doc.Regenerate()
        elevations_col = []
        elevation_count = ["A", "B", "C", "D"]
        if elev_as_sections:
            room_bb_loop = geo.room_bb_outlines(room)
            offset_in = DB.CurveLoop.CreateViaOffset(room_bb_loop, -chosen_crop_offset, DB.XYZ.BasisZ)
            for border in offset_in:
                # create a bbox parallel to the border
                sb = database.create_parallel_bbox(border, room)

                # if form.values["sec_or_elev"] == "Sections":
                new_section = DB.ViewSection.CreateSection(revit.doc, section_type.Id, sb)
                elevations_col.append(new_section)

        else:

            new_marker = DB.ElevationMarker.CreateElevationMarker(
                revit.doc, elevation_type.Id, room_location, view_scale
            )
            # rotate marker
            revit.doc.Regenerate()
            marker_axis = DB.Line.CreateBound(
                room_location, room_location + DB.XYZ.BasisZ
            )
            rotated = new_marker.Location.Rotate(marker_axis, angle)
            revit.doc.Regenerate()

            for i in range(4):
                elevation = new_marker.CreateElevation(revit.doc, viewplan.Id, i)
                elevations_col.append(elevation)

        # Rename elevations

        for el, i in izip(elevations_col, elevation_count):
            el.Scale = view_scale
            el_suffix = " Elevation " + i
            el.Name = database.unique_view_name(room_name_nr, el_suffix)
            database.set_anno_crop(el)

        sheet = database.create_sheet(chosen_sheet_nr, room_name_nr, chosen_tb.Id)

    # get positions on sheet
    loc = locator.Locator(sheet, titleblock_offset, tb_ori, layout_ori)
    plan_position = loc.plan
    RCP_position = loc.rcp
    elevations_positions = loc.elevations
    threeD_position = loc.threeD

    elevations = []  # collect all elevations we create

    # create viewports on sheet
    with revit.Transaction("Add Views to Sheet", revit.doc):
        # apply view template
        database.apply_vt(viewplan, chosen_vt_plan)
        database.apply_vt(viewRCP, chosen_vt_rcp_plan)

        # place view on sheet
        place_plan = DB.Viewport.Create(revit.doc, sheet.Id, viewplan.Id, plan_position)
        place_RCP = DB.Viewport.Create(revit.doc, sheet.Id, viewRCP.Id, RCP_position)
        if layout_ori == "Cross":
            place_threeD = DB.Viewport.Create(revit.doc, sheet.Id, threeD.Id, threeD_position)

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
        if layout_ori == "Cross":
            loc.realign_pos(revit.doc, [place_threeD], [threeD_position])

        print("Sheet : {0} \t Room {1} ".format(output.linkify(sheet.Id), room_name_nr))
