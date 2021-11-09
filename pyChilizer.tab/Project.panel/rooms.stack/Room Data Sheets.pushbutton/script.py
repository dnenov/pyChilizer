__title__ = "Room Data Sheets"
__doc__ = "Creates room plans and elevations and places them on a sheet."

from pyrevit import revit, DB, script, forms, HOST_APP
from rpw.ui.forms import (FlexForm, Label, TextBox, Button)
import helper
from pyrevit.revit.db import query
from itertools import izip
from collections import namedtuple
import math
from Autodesk.Revit import Exceptions

output = script.get_output()
logger = script.get_logger()
bound_opt = DB.SpatialElementBoundaryOptions()
# use preselected elements, filtering rooms only
selection = helper.select_rooms_filter()

# DONE: choose longest curve to rotate by, also if it's a line
# DONE: try using room boundaries for crop, if fails use BBox
# DONE: offset boundary curve - done
# DONE: ask for scale and sheet number

# ask for settings

titleblock = forms.select_titleblocks(doc=revit.doc)

if not selection:
    forms.alert('You need to select at least one Room.', exitscript=True)

col_view_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType).WhereElementIsElementType()
floor_plan_type = [vt for vt in col_view_types if vt.FamilyName == "Floor Plan"][0]

components = [
    Label('Sheet Number'),
    TextBox('sheet_number', Text='1000'),
    Button("Select")
]

form = FlexForm('Set Sheet Number', components)
form.show()

chosen_sheet_nr = form.values['sheet_number']

plan_type = DB.ViewType.FloorPlan
crop_offset = 1
elevation_type = \
    [vt for vt in DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType) if vt.FamilyName == "Elevation"][0]
view_scale = 25
sheet_num = "0001"
offset_distance = 1

# approximate positions for viewports on an A1 sheet
plan_position = DB.XYZ(0.282, 0.434, 0)
elevations_positions = [DB.XYZ(1.14, 1.25, 0), DB.XYZ(1.805, 1.25, 0), DB.XYZ(1.14, 0.434, 0), DB.XYZ(1.805, 0.434, 0)]

for room in selection:

    with revit.Transaction("Create Plan", revit.doc):
        level = room.Level

        # Create Floor Plan
        viewplan = DB.ViewPlan.Create(revit.doc, floor_plan_type.Id, level.Id)
        viewplan.Scale = view_scale
        # choose one longest curve to use as reference for rotation
        longest_boundary = helper.get_longest_boundary(room)
        p = longest_boundary.GetEndPoint(0)
        q = longest_boundary.GetEndPoint(1)
        v = q - p

        bbox_angle = v.AngleTo(DB.XYZ.BasisY)
        # correct angles
        if helper.degree_conv(bbox_angle) > 90:
            bbox_angle = bbox_angle - math.radians(90)
        elif helper.degree_conv(bbox_angle) < 45:
            bbox_angle = - bbox_angle
        else:
            bbox_angle = bbox_angle
        # get viewplan bbox, center
        bbox = room.get_BoundingBox(viewplan)
        center = 0.5 * (bbox.Max + bbox.Min)
        axis = DB.Line.CreateBound(center, center + DB.XYZ.BasisZ)
    # find crop box element (method with transactions)
    crop_box_el = helper.find_crop_box(viewplan)

    with revit.Transaction("Rotate Plan", revit.doc):
        rotated = DB.ElementTransformUtils.RotateElement(revit.doc, crop_box_el.Id, axis, bbox_angle)
        viewplan.CropBoxActive = True
        revit.doc.Regenerate()

        room_boundaries = helper.get_room_bound(room)
        if room_boundaries:
            try:
                offset_boundaries = room_boundaries.CreateViaOffset(room_boundaries, offset_distance, DB.XYZ(0, 0, 1))
                crop_shape = viewplan.GetCropRegionShapeManager()
                crop_shape.SetCropShape(offset_boundaries)
                revit.doc.Regenerate()
            except Exceptions.InternalException:
                new_bbox = room.get_BoundingBox(viewplan)
                viewplan.CropBox = new_bbox
        else:
            new_bbox = room.get_BoundingBox(viewplan)
            viewplan.CropBox = new_bbox

        # Rename Floor Plan
        room_name_nr = room.Number + " - " + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        viewplan_name = room_name_nr + " Plan"
        while helper.get_view(viewplan_name):
            viewplan_name = viewplan_name + " Copy 1"
        viewplan.Name = viewplan_name
        helper.set_anno_crop(viewplan)

        # Create Elevations
        revit.doc.Regenerate()
        elevations_col = []
        marker_position = room.Location.Point
        new_marker = DB.ElevationMarker.CreateElevationMarker(revit.doc, elevation_type.Id, marker_position, view_scale)
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
        marker_axis = DB.Line.CreateBound(marker_position, marker_position + DB.XYZ.BasisZ)
        rotated = new_marker.Location.Rotate(marker_axis, bbox_angle)
        revit.doc.Regenerate()

        sheet = helper.create_sheet(chosen_sheet_nr, room_name_nr, titleblock)

    with revit.Transaction("Add Views to Sheet", revit.doc):
        place_plan = DB.Viewport.Create(revit.doc, sheet.Id, viewplan.Id, plan_position)
        for i, pos in izip(elevations_col, elevations_positions):
            # todo: correct position to bottom left corner
            place_elevation = DB.Viewport.Create(revit.doc, sheet.Id, i.Id, pos)
        print("Sheet : {0} \t Room {1} ".format(output.linkify(sheet.Id),room_name_nr))
