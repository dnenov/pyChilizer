from pyrevit import revit, DB, script, forms
from rpw.ui.forms import FlexForm, Label, TextBox, Button, ComboBox, CheckBox, Separator
import rdspluslocator, rdsplusui
from itertools import izip
import sys
from pychilizer import units, select, geo, database
from Autodesk.Revit import Exceptions
import math

ui = rdsplusui.UI(script)
ui.is_metric = units.is_metric
doc = __revit__.ActiveUIDocument.Document

MINIMAL_LENGTH = 1.5
UNIQUE_BORDERS_TOLERANCE = 10 / 304.8
ELEVATION_SPACING = 0.3
ELEVATION_ID = 0  # elevation on the marker placed facing left
VIEW_SCALE = 50
RDS_FLOOR_PLAN_TYPE_NAME = "RDS Floor Plan Type"

def elevation_offsets(el_widths, spacing):
    el_offsets = [el_widths[0] + spacing]
    for i in range(len(el_widths) - 1):
        offset = (el_widths[i] + el_widths[i + 1]) / 2 + spacing
        el_offsets.append(offset)
    return el_offsets


def get_view_width_scaled(view):
    crop_bbox = view.CropBox
    real_width = crop_bbox.Max.X - crop_bbox.Min.X
    scaled_width = real_width / view.Scale
    return scaled_width


def get_view_family_type_by_name(view_family_category, name, doc=revit.doc):
    # get ViewFamilyType by type and name
    all_view_family_types = database.get_view_family_types(view_family_category, doc)
    for view_fam_type in all_view_family_types:
        if view_fam_type.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME).AsValueString() == name:
            return view_fam_type


output = script.get_output()
logger = script.get_logger()

selection = select.select_with_cat_filter(DB.BuiltInCategory.OST_Rooms, "Pick Rooms for Room Data Sheets")

# collect all view templates for plans and sections
viewsections = DB.FilteredElementCollector(doc).OfClass(DB.ViewSection)  # collect sections
ui.viewsection_dict = {v.Name: v for v in viewsections if v.IsTemplate}  # only fetch the IsTemplate sections
viewplans = DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan)  # collect plans
ui.viewplan_dict = {v.Name: v for v in viewplans if v.IsTemplate}  # only fetch IsTemplate plans
# collect viewport types
ui.viewport_dict = {database.get_name(v): v for v in
                    database.get_viewport_types(doc)}  # use a special collector w viewport param
ui.set_vp_types()
# add none as an option
ui.viewsection_dict["<None>"] = None
ui.viewplan_dict["<None>"] = None
ui.set_viewtemplates()

# collect titleblocks in a dictionary
titleblocks = DB.FilteredElementCollector(doc).OfCategory(
    DB.BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType().ToElements()
if not titleblocks:
    forms.alert("There are no Titleblocks loaded in the model.", exitscript=True)
ui.titleblock_dict = {'{} : {}'.format(tb.FamilyName, revit.query.get_name(tb)): tb for tb in titleblocks}
ui.set_titleblocks()

# get units for Crop Offset variable
if units.is_metric(doc):
    unit_sym = " [mm]"
else:
    unit_sym = " [decimal feet]"

components = [
    Label("Select Titleblock"),
    ComboBox(name="tb", options=sorted(ui.titleblock_dict), default=database.tb_name_match(ui.titleblock, doc)),
    Label("Sheet Number"),
    TextBox("sheet_number", Text=ui.sheet_number),
    Label("Crop offset" + unit_sym),
    TextBox("crop_offset", Text=str(ui.crop_offset)),
    Label("Titleblock (internal) offset" + unit_sym),
    TextBox("titleblock_offset", Text=str(ui.titleblock_offset)),
    Label("Titleblock orientation"),
    ComboBox(name="tb_orientation", options=ui.tblock_orientation, default=ui.titleblock_orientation),
    Separator(),
    Label("Elevation Marker offset from boundary" + unit_sym),
    TextBox("marker_offset", Text=str(ui.marker_offset)),
    Separator(),
    Label("View Template for Plans"),
    ComboBox(name="vt_plans", options=sorted(ui.viewplan_dict), default=database.vt_name_match(ui.viewplan, doc)),
    Label("View Template for Reflected Ceiling Plans"),
    ComboBox(name="vt_rcp_plans", options=sorted(ui.viewplan_dict),
             default=database.vt_name_match(ui.viewceiling, doc)),
    Label("View Template for Elevations"),
    ComboBox(name="vt_elevs", options=sorted(ui.viewsection_dict), default=database.vt_name_match(ui.viewsection, doc)),
    Label("Viewport Type"),
    ComboBox(name="vp_types", options=sorted(ui.viewport_dict), default=database.vp_name_match(ui.viewport, doc)),
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
    chosen_vp_type = ui.viewport_dict[form.values["vp_types"]]
    chosen_crop_offset = units.correct_input_units(form.values["crop_offset"], doc)
    chosen_marker_offset = units.correct_input_units(form.values["marker_offset"], doc)
    titleblock_offset = units.correct_input_units(form.values["titleblock_offset"], doc)
    tb_orientation = form.values["tb_orientation"]
else:
    sys.exit()


# collect and take the first elevation type, rcp type
ceiling_plan_type = database.get_view_family_types(DB.ViewFamily.CeilingPlan, doc)[0]
elev_type = database.get_view_family_types(DB.ViewFamily.Elevation, doc)[0]
# look for RDS floor plan type
rds_floor_plan_type = get_view_family_type_by_name(DB.ViewFamily.FloorPlan, RDS_FLOOR_PLAN_TYPE_NAME, doc)
if not rds_floor_plan_type:
    # duplicate floor type and create one without the template overrides
    some_fl_plan_type = database.get_view_family_types(DB.ViewFamily.FloorPlan, doc)[0]
    with revit.Transaction("Duplicate Floor Plan Type", doc):
        rds_floor_plan_type = some_fl_plan_type.Duplicate(RDS_FLOOR_PLAN_TYPE_NAME)
        rds_floor_plan_type.DefaultTemplateId = DB.ElementId(-1)

# get default elevation template
default_elevation_template = doc.GetElement(elev_type.DefaultTemplateId)
if default_elevation_template:
    check_room_vis = default_elevation_template.GetCategoryHidden(DB.ElementId(-2000160))
    # check if rooms are hidden in the default template and disable it if yes
    if check_room_vis:
        if forms.alert(
                "To proceed, we need to remove a Default View Template associated with Elevation Type. Is that cool with ya?",
                ok=False, yes=True, no=True, exitscript=True):
            with revit.Transaction("Remove ViewTemplate"):
                elev_type.DefaultTemplateId = DB.ElementId(-1)

ui.set_config("sheet_number", chosen_sheet_nr)
ui.set_config("crop_offset", form.values["crop_offset"])
ui.set_config("marker_offset", form.values["marker_offset"])
ui.set_config("titleblock_offset", form.values["titleblock_offset"])
ui.set_config("titleblock_orientation", tb_orientation)
ui.set_config("titleblock", form.values["tb"])
ui.set_config("viewport", form.values["vp_types"])
ui.set_config("viewplan", form.values["vt_plans"])
ui.set_config("viewceiling", form.values["vt_rcp_plans"])
ui.set_config("viewsection", form.values["vt_elevs"])

for room in selection:
    with revit.Transaction("Create Plan", doc):
        level = room.Level
        rm_loc = room.Location.Point
        room_angle = geo.room_rotation_angle(room)  # helper method get room rotation by longest boundary

        # Create Floor Plan
        viewplan = DB.ViewPlan.Create(doc, rds_floor_plan_type.Id, level.Id)
        viewplan.Scale = VIEW_SCALE

        # Create Reflected Ceiling Plan
        viewRCP = DB.ViewPlan.Create(doc, ceiling_plan_type.Id, level.Id)
        viewRCP.Scale = VIEW_SCALE

    # find crop box element (method with transactions, must be outside transaction)
    crop_box_plan = geo.find_crop_box(viewplan)
    crop_box_rcp = geo.find_crop_box(viewRCP)

    with revit.Transaction("Crop and Create Elevations", doc):
        # rotate the view plan
        axis = geo.get_bb_axis_in_view(room, viewplan)  # get the axis for rotation
        rotated_plan = DB.ElementTransformUtils.RotateElement(
            doc, crop_box_plan.Id, axis, room_angle
        )
        # rotate RCP
        rotated_rcp = DB.ElementTransformUtils.RotateElement(
            doc, crop_box_rcp.Id, axis, room_angle
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
                    room_boundaries, chosen_crop_offset, DB.XYZ(0, 0, 1))
                crsm_plan.SetCropShape(offset_loop)
                crsm_rcp.SetCropShape(offset_loop)
            # for some shapes the offset is not obvious and will fail, then use BBox method:
            except:
                # using a helper method, get the outlines of the room's bounding box,
                rotated_crop_loop = geo.room_bb_outlines(room, room_angle)
                # offset the curve loop with given offset
                offset_loop = DB.CurveLoop.CreateViaOffset(rotated_crop_loop, chosen_crop_offset, DB.XYZ.BasisZ)
                # set the loop as Crop Shape of the view using CropRegionShapeManager
                crsm_plan.SetCropShape(offset_loop)
                crsm_rcp.SetCropShape(offset_loop)

        # Construct View Names
        room_name_nr = (
                room.Number
                + " - "
                + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString())

        # rename views
        viewplan.Name = database.unique_view_name(room_name_nr, suffix=" Plan")
        viewRCP.Name = database.unique_view_name(room_name_nr, suffix=" Reflected Ceiling Plan")

        # activate annotation crop
        database.set_anno_crop(viewplan)
        database.set_anno_crop(viewRCP)

        # Create Elevations
        elevations_col = []

        # discard segments lying on the same axis of the room - not in scope anymore
        # unique_borders = geo.get_unique_borders(room_boundaries, UNIQUE_BORDERS_TOLERANCE)

        border_widths = []
        for border in room_boundaries:

            if isinstance(border, DB.Line) and border.Length >= MINIMAL_LENGTH:
                viewplan.Scale = VIEW_SCALE

                # elevation marker position - middle of the boundary
                border_center = border.Evaluate(0.5, True)

                # offset inwards and check if it's the right side (check if inside room)
                marker_position = geo.offset_curve_inwards_into_room(border, room, chosen_marker_offset).Evaluate(0.5, True)

                # create marker
                new_marker = DB.ElevationMarker.CreateElevationMarker(doc, elev_type.Id, marker_position, VIEW_SCALE)

                # create 1 elevation
                try:
                    elevation = new_marker.CreateElevation(doc, viewplan.Id, ELEVATION_ID)
                    elevations_col.append(elevation)
                except Exceptions.ArgumentException:
                    forms.alert("Elevation Marker is invalid. Please review the Elevation Marker and retry",
                                exitscript=True)

                # rotate the marker to face the boundary
                geo.orient_elevation_to_line(doc, new_marker, marker_position, border, ELEVATION_ID, viewplan)


                doc.Regenerate()
                # create a bbox parallel to the border
                geo.set_crop_to_boundary(room, border, elevation, chosen_crop_offset, doc)
                database.apply_vt(elevation, chosen_vt_elevation)
                # record the boundary lengths (also elevation widths) for later
                border_widths.append(get_view_width_scaled(elevation))

        # Rename elevations - Room name Elevation N
        elevation_count = database.get_alphabetic_labels(len(elevations_col))
        for el, i in izip(elevations_col, elevation_count):
            el.Scale = VIEW_SCALE
            el_suffix = " Elevation " + i
            el.Name = database.unique_view_name(room_name_nr, el_suffix)
            database.set_anno_crop(el)

        sheet = database.create_sheet(chosen_sheet_nr, room_name_nr, chosen_tb.Id)

    elevation_widths = elevation_offsets(border_widths, ELEVATION_SPACING)

    # get positions on sheet
    loc = rdspluslocator.Locator(sheet, titleblock_offset, tb_orientation, elevation_widths)
    plan_position = loc.plan
    RCP_position = loc.rcp
    elev_positions = loc.elevations
    elevations = []  # collect all elevations we create

    with revit.Transaction("Add Views to Sheet", doc):
        # apply view template
        database.apply_vt(viewplan, chosen_vt_plan)
        database.apply_vt(viewRCP, chosen_vt_rcp_plan)

        # place view on sheet
        place_plan = DB.Viewport.Create(doc, sheet.Id, viewplan.Id, plan_position)
        place_RCP = DB.Viewport.Create(doc, sheet.Id, viewRCP.Id, RCP_position)

        for el, pos, i in izip(elevations_col, elev_positions, elevation_count):
            # place elevations
            place_elevation = DB.Viewport.Create(doc, sheet.Id, el.Id, pos)

            # set viewport detail number
            place_elevation.get_Parameter(
                DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER
            ).Set(i)
            elevations.append(place_elevation)
            doc.Regenerate()

        # new: change viewport types
        for vp in elevations + [place_plan] + [place_RCP]:
            vp.ChangeTypeId(chosen_vp_type.Id)

        doc.Regenerate()

        # realign the viewports to their desired positions
        loc.realign_pos(doc, [place_plan], [plan_position])
        loc.realign_pos(doc, [place_RCP], [RCP_position])
        # loc.realign_pos(doc, elevations, elev_positions)

        print("Sheet : {0} \t Room {1} ".format(output.linkify(sheet.Id), room_name_nr))
