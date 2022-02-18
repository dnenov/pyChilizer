import math

from pyrevit import revit, DB, script
from rpw.ui.forms import FlexForm, Label, TextBox, Button, ComboBox, CheckBox, Separator
import locator, ui
from itertools import izip
import sys
from pychilizer import units, select, geo, database


ui = ui.UI(script)
ui.is_metric = units.is_metric

doc = __revit__.ActiveUIDocument.Document

output = script.get_output()
logger = script.get_logger()  # helps to debug script, not used

selection = select.select_with_cat_filter(DB.BuiltInCategory.OST_Rooms, "Pick Rooms for Room Data Sheets")

# collect all view templates for plans and sections
viewsections = DB.FilteredElementCollector(doc).OfClass(DB.ViewSection)  # collect sections
ui.viewsection_dict = {v.Name: v for v in viewsections if v.IsTemplate}  # only fetch the IsTemplate sections

viewplans = DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan)  # collect plans
ui.viewplan_dict = {v.Name: v for v in viewplans if v.IsTemplate}  # only fetch IsTemplate plans

# TODO
# viewport_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.Viewport).WhereElementIsElementType() # collect all viewport types
# ui.viewport_dict = {v.Name: v for v in viewport_types}  

# add none as an option
ui.viewsection_dict["<None>"] = None
ui.viewplan_dict["<None>"] = None

ui.set_viewtemplates()

# collect titleblocks in a dictionary
titleblocks = DB.FilteredElementCollector(doc).OfCategory(
    DB.BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType()
ui.titleblock_dict = {'{}: {}'.format(tb.FamilyName, revit.query.get_name(tb)): tb for tb in titleblocks}
ui.set_titleblocks()


# collect and take the first view plan type, elevation type, set default scale
fl_plan_type = database.get_view_family_types(DB.ViewFamily.FloorPlan)[0]
ceiling_plan_type = database.get_view_family_types(DB.ViewFamily.CeilingPlan)[0]
elev_type = database.get_view_family_types(DB.ViewFamily.Elevation)[0]
section_type = database.get_view_family_types(DB.ViewFamily.Section)[0]

view_scale = 50

# get units for Crop Offset variable
if units.is_metric(doc):
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
    with revit.Transaction("Create Plan", doc):
        level = room.Level
        rm_loc = room.Location.Point
        angle = geo.room_rotation_angle(room) # helper method get room rotation by longest boundary

        # Create Floor Plan
        viewplan = DB.ViewPlan.Create(doc, fl_plan_type.Id, level.Id)
        viewplan.Scale = view_scale

        # Create Reflected Ceiling Plan
        viewRCP = DB.ViewPlan.Create(doc, ceiling_plan_type.Id, level.Id)
        viewRCP.Scale = view_scale

        if layout_ori == "Cross": # for cross layout, add the 3D axo
            threeD = geo.create_room_axo_rotate(room, angle, view_scale)

    # find crop box element (method with transactions, must be outside transaction)
    crop_box_plan = geo.find_crop_box(viewplan)
    crop_box_rcp = geo.find_crop_box(viewRCP)

    with revit.Transaction("Crop and Create Elevations", doc):
        # rotate the view plan
        axis = geo.get_bb_axis_in_view(room, viewplan)  # get the axis for rotation
        rotated_plan = DB.ElementTransformUtils.RotateElement(
            doc, crop_box_plan.Id, axis, angle
        )
        # rotate RCP
        rotated_rcp = DB.ElementTransformUtils.RotateElement(
            doc, crop_box_rcp.Id, axis, angle
        )

        viewplan.CropBoxActive = True
        viewRCP.CropBoxActive = True
        doc.Regenerate()

        room_boundaries = geo.get_room_bound(room)

        if room_boundaries:
            crsm_plan = viewplan.GetCropRegionShapeManager()
            crsm_rcp = viewRCP.GetCropRegionShapeManager()
            # try offsetting boundaries (to include walls in plan view)
            try:
                offset_loop = room_boundaries.CreateViaOffset(
                    room_boundaries, chosen_crop_offset, DB.XYZ(0, 0, 1)
                )

                crsm_plan.SetCropShape(offset_loop)
                crsm_rcp.SetCropShape(offset_loop)
            # for some shapes the offset is not obvious and will fail, then use BBox method:
            except:
                # using a helper method, get the outlines of the room's bounding box,
                rotated_crop_loop = geo.room_bb_outlines(room, angle)
                # offset the curve loop with given offset
                offset_loop = DB.CurveLoop.CreateViaOffset(rotated_crop_loop, chosen_crop_offset, DB.XYZ.BasisZ)
                # set the loop as Crop Shape of the view using CropRegionShapeManager

                crsm_plan.SetCropShape(offset_loop)
                crsm_rcp.SetCropShape(offset_loop)

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
        elevations_col = []
        elevation_count = ["A", "B", "C", "D"]
        if elev_as_sections:
            elevation_count = database.shift_list(elevation_count, 1)
            room_bb_loop = geo.room_bb_outlines(room, angle)
            offset_in = DB.CurveLoop.CreateViaOffset(room_bb_loop, -chosen_crop_offset, DB.XYZ.BasisZ)
            for border in offset_in:
                # create a bbox parallel to the border
                sb = database.create_parallel_bbox(border, room)
                new_section = DB.ViewSection.CreateSection(doc, section_type.Id, sb)
                elevations_col.append(new_section)
        else:
            # create marker
            new_marker = DB.ElevationMarker.CreateElevationMarker(doc, elev_type.Id, rm_loc, view_scale)
            # create 4 elevations
            for i in range(4):
                elevation = new_marker.CreateElevation(doc, viewplan.Id, i)
                elevations_col.append(elevation)

            # rotate marker with room rotation angle
            doc.Regenerate()
            marker_axis = DB.Line.CreateBound(rm_loc, rm_loc + DB.XYZ.BasisZ)
            new_marker.Location.Rotate(marker_axis, angle)
            doc.Regenerate()
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
    elev_positions = loc.elevations
    # if using sections, shift the positions with 1 index
    if elev_as_sections:
        elev_positions = database.shift_list(elev_positions, 1)
    threeD_position = loc.threeD

    elevations = []  # collect all elevations we create

    with revit.Transaction("Add Views to Sheet", doc):
        # apply view template
        database.apply_vt(viewplan, chosen_vt_plan)
        database.apply_vt(viewRCP, chosen_vt_rcp_plan)

        # place view on sheet
        place_plan = DB.Viewport.Create(doc, sheet.Id, viewplan.Id, plan_position)
        place_RCP = DB.Viewport.Create(doc, sheet.Id, viewRCP.Id, RCP_position)
        if layout_ori == "Cross":
            place_threeD = DB.Viewport.Create(doc, sheet.Id, threeD.Id, threeD_position)

        for el, pos, i in izip(elevations_col, elev_positions, elevation_count):
            # place elevations
            place_elevation = DB.Viewport.Create(doc, sheet.Id, el.Id, pos)

            # if user selected, rotate elevations
            if elev_rotate and i == "A" and layout_ori == "Cross":
                place_elevation.Rotation = DB.ViewportRotation.Counterclockwise
            if elev_rotate and i == "C" and layout_ori == "Cross":
                place_elevation.Rotation = DB.ViewportRotation.Clockwise

            # set viewport detail number
            place_elevation.get_Parameter(
                DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER
            ).Set(i)
            elevations.append(place_elevation)
            doc.Regenerate()
            room_bb = room.get_BoundingBox(el)
            geo.set_crop_to_bb(room, el, crop_offset=chosen_crop_offset)
            database.apply_vt(el, chosen_vt_elevation)

        doc.Regenerate()

        # realign the viewports to their desired positions
        loc.realign_pos(doc, [place_plan], [plan_position])
        loc.realign_pos(doc, [place_RCP], [RCP_position])
        loc.realign_pos(doc, elevations, elev_positions)
        if layout_ori == "Cross":
            loc.realign_pos(doc, [place_threeD], [threeD_position])

        print("Sheet : {0} \t Room {1} ".format(output.linkify(sheet.Id), room_name_nr))