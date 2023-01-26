from pyrevit import revit, DB, script, forms
from rpw.ui.forms import FlexForm, Label, TextBox, Button, ComboBox, CheckBox, Separator
import locator, ui
from itertools import izip
import sys
from pychilizer import units, select, geo, database
from Autodesk.Revit import Exceptions
import math



ui = ui.UI(script)
ui.is_metric = units.is_metric
doc = __revit__.ActiveUIDocument.Document
MINIMAL_LENGTH = 1.5
OFFSET_INWARDS = 1
UNIQUE_BORDERS_TOLERANCE = 10/304.8
ELEVATION_SPACING = 0.3
ELEVATION_ID = 0

def get_alphabetic_labels(nr):
    alphabet = [chr(i) for i in range(65,91)]
    double_alphabet = []
    for i in range(26):
        c1 = alphabet[i]
        for j in range(26):
            c2 = alphabet[j]
            l = c1+c2
            double_alphabet.append(l)
    labels = []
    if nr<=26:
        labels = alphabet[:nr]
    elif nr>26:
        labels = double_alphabet[:nr]
    return labels


def elevation_offsets(el_widths, spacing):
    el_offsets = []
    for i in range(len(el_widths)-1):
        offset = (el_widths[i]+el_widths[i+1])/2+spacing
        el_offsets.append(offset)
    return el_offsets


def orient_elevation_to_line (elevation_marker, line, elevation_id):
    # get the elevation with the elevation id
    elevation_view = doc.GetElement(elevation_marker.GetViewId(elevation_id))
    # get the view direction of the elevation view (facing the viewer)
    view_direction = elevation_view.ViewDirection
    # note: the origin of the elevation view is NOT the center of the marker
    # TODO: ORIGIN = BAD
    bb = elevation_marker.get_BoundingBox(revit.active_view)
    center = (bb.Max+bb.Min)/2

    # project the origin onto the line and get closest point
    project = line.Project(center)
    project_point = project.XYZPoint
    # construct a line from from the projected point to origin and get its vector
    projection_direction = DB.Line.CreateBound(project_point, center).Direction
    vectors_angle = view_direction.AngleOnPlaneTo(projection_direction, DB.XYZ.BasisZ)
    # calculate the rotation angle
    rotation_angle = vectors_angle - math.radians(360)

    marker_axis = DB.Line.CreateBound(center, center + DB.XYZ.BasisZ)
    elevation_marker.Location.Rotate(marker_axis, rotation_angle)
    return elevation_marker


output = script.get_output()
logger = script.get_logger()  # helps to debug script, not used

selection = select.select_with_cat_filter(DB.BuiltInCategory.OST_Rooms, "Pick Rooms for Room Data Sheets")

# collect all view templates for plans and sections
viewsections = DB.FilteredElementCollector(doc).OfClass(DB.ViewSection)  # collect sections
ui.viewsection_dict = {v.Name: v for v in viewsections if v.IsTemplate}  # only fetch the IsTemplate sections
viewplans = DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan)  # collect plans
ui.viewplan_dict = {v.Name: v for v in viewplans if v.IsTemplate}  # only fetch IsTemplate plans

# TODO: fix the default value
ui.viewport_dict = {database.get_name(v): v for v in
                    database.get_viewport_types(doc)}  # use a special collector w viewport param
# add none as an option
ui.viewsection_dict["<None>"] = None
ui.viewplan_dict["<None>"] = None
ui.set_viewtemplates()

# collect titleblocks in a dictionary
titleblocks = DB.FilteredElementCollector(doc).OfCategory(
    DB.BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType().ToElements()
if not titleblocks:
    forms.alert("There are no Titleblocks loaded in the model.", exitscript=True)
ui.titleblock_dict = {'{}: {}'.format(tb.FamilyName, revit.query.get_name(tb)): tb for tb in titleblocks}
ui.set_titleblocks()

view_scale = 50

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
    Label("View Template for Plans"),
    ComboBox(name="vt_plans", options=sorted(ui.viewplan_dict), default=database.vt_name_match(ui.viewplan, doc)),
    Label("View Template for Reflected Ceiling Plans"),
    ComboBox(name="vt_rcp_plans", options=sorted(ui.viewplan_dict),
             default=database.vt_name_match(ui.viewceiling, doc)),
    Label("View Template for Elevations"),
    ComboBox(name="vt_elevs", options=sorted(ui.viewsection_dict), default=database.vt_name_match(ui.viewsection, doc)),
    Label("Viewport Type"),
    ComboBox(name="vp_types", options=sorted(ui.viewport_dict)),
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
    titleblock_offset = units.correct_input_units(form.values["titleblock_offset"], doc)
    tb_orientation = form.values["tb_orientation"]
else:
    sys.exit()

# collect and take the first view plan type, elevation type, set default scale
fl_plan_type = database.get_view_family_types(DB.ViewFamily.FloorPlan, doc)[0]
ceiling_plan_type = database.get_view_family_types(DB.ViewFamily.CeilingPlan, doc)[0]
elev_type = database.get_view_family_types(DB.ViewFamily.Elevation, doc)[0]

# get default template
def_temp = doc.GetElement(elev_type.DefaultTemplateId)
if def_temp:
    check_room_vis = def_temp.GetCategoryHidden(DB.ElementId(-2000160))
    # check if rooms are hidden in the default template and disable it if yes
    if check_room_vis:
        if forms.alert(
                "To proceed, we need to remove a Default View Template associated with Elevation / Section View Type. Is that cool with ya?",
                ok=False, yes=True, no=True, exitscript=True):
            with revit.Transaction("Remove ViewTemplate"):
                elev_type.DefaultTemplateId = DB.ElementId(-1)

ui.set_config("sheet_number", chosen_sheet_nr)
ui.set_config("crop_offset", form.values["crop_offset"])
ui.set_config("titleblock_offset", form.values["titleblock_offset"])
ui.set_config("titleblock_orientation", tb_orientation)
ui.set_config("titleblock", form.values["tb"])
ui.set_config("viewplan", form.values["vt_plans"])
ui.set_config("viewceiling", form.values["vt_rcp_plans"])
ui.set_config("viewsection", form.values["vt_elevs"])

for room in selection:
    with revit.Transaction("Create Plan", doc):
        level = room.Level
        rm_loc = room.Location.Point
        room_angle = geo.room_rotation_angle(room)  # helper method get room rotation by longest boundary

        # Create Floor Plan
        viewplan = DB.ViewPlan.Create(doc, fl_plan_type.Id, level.Id)
        viewplan.Scale = view_scale

        # Create Reflected Ceiling Plan
        viewRCP = DB.ViewPlan.Create(doc, ceiling_plan_type.Id, level.Id)
        viewRCP.Scale = view_scale

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
                    room_boundaries, chosen_crop_offset, DB.XYZ(0, 0, 1)
                )

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
                + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        )

        # rename views
        viewplan.Name = database.unique_view_name(room_name_nr, suffix=" Plan")
        viewRCP.Name = database.unique_view_name(room_name_nr, suffix=" Reflected Ceiling Plan")

        # activate annotation crop
        database.set_anno_crop(viewplan)
        database.set_anno_crop(viewRCP)

        # Create Elevations
        elevations_col = []
        # THIS PART IS DIFFERENT FROM CLASSIC
        #room_bb_loop = geo.room_bb_outlines(room, angle) # this is not what i need
        # offset_in = DB.CurveLoop.CreateViaOffset(room_bb_loop, -OFFSET_INWARDS, DB.XYZ.BasisZ) # probably cannot offset room bound

        # discard segments lying on the same axis of the room
        #TODO: test
        unique_borders = geo.get_unique_borders(room_boundaries, UNIQUE_BORDERS_TOLERANCE)
        border_widths = []
        for border in unique_borders:

            if isinstance(border, DB.Line) and border.Length >= MINIMAL_LENGTH:
                # record the boundary lengths (also elevation widths) for later
                border_widths.append(border.Length)
                # elevation marker position
                #TODO: offset from wall
                border_center = border.Evaluate(0.5, True)

                offset = border.CreateOffset(OFFSET_INWARDS, DB.XYZ(0,0,1))
                marker_position = offset.Evaluate(0.5, True)
                if not room.IsPointInRoom(marker_position):
                    offset = border.CreateOffset(-OFFSET_INWARDS, DB.XYZ(0,0,1))
                    marker_position = offset.Evaluate(0.5, True)

                # create marker
                new_marker = DB.ElevationMarker.CreateElevationMarker(doc, elev_type.Id, marker_position, view_scale)
                # create 1 elevation
                try:
                    elevation = new_marker.CreateElevation(doc, viewplan.Id, ELEVATION_ID)
                    elevations_col.append(elevation)

                except Exceptions.ArgumentException:
                    forms.alert("Elevation Marker is invalid. Please review the Elevation Marker and retry",
                                exitscript=True)

                # rotate marker with room rotation angle
                # TODO: still some cases the rotation is wrong
                orient_elevation_to_line(new_marker,border,ELEVATION_ID)
                # TODO: crop elevations
                doc.Regenerate()
        # Rename elevations - Room name Elevation N
        elevation_count = get_alphabetic_labels(len(elevations_col))
        for el, i in izip(elevations_col, elevation_count):
            el.Scale = view_scale
            el_suffix = " Elevation " + i
            el.Name = database.unique_view_name(room_name_nr, el_suffix)
            database.set_anno_crop(el)

        sheet = database.create_sheet(chosen_sheet_nr, room_name_nr, chosen_tb.Id)
    #todo: substitute this
    elevation_widths = [1]* len(elevations_col)
    # elevation_widths = elevation_offsets(border_widths, ELEVATION_SPACING)

    # get positions on sheet
    loc = locator.Locator(sheet, titleblock_offset, tb_orientation, elevation_widths)
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
            #TODO: temp disable
            # geo.set_crop_to_bb(room, el, chosen_crop_offset, doc)
            database.apply_vt(el, chosen_vt_elevation)

        # new: change viewport types
        for vp in elevations + [place_plan] + [place_RCP]:
            vp.ChangeTypeId(chosen_vp_type.Id)

        doc.Regenerate()

        # realign the viewports to their desired positions
        loc.realign_pos(doc, [place_plan], [plan_position])
        loc.realign_pos(doc, [place_RCP], [RCP_position])
        loc.realign_pos(doc, elevations, elev_positions)

        print("Sheet : {0} \t Room {1} ".format(output.linkify(sheet.Id), room_name_nr))
