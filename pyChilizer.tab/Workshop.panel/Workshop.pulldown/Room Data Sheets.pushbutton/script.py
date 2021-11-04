__title__ = "Room Data Sheets"
__doc__ = "Room Data Sheets"

from pyrevit import revit, DB, script, forms, HOST_APP
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
import helper
from pyrevit.revit.db import query
from itertools import izip
from collections import namedtuple
import math

output = script.get_output()
logger = script.get_logger()
DEFAULT_CROP = '0.75'  # About 9"
bound_opt = DB.SpatialElementBoundaryOptions()
# use preselected elements, filtering rooms only
selection = helper.select_rooms_filter()
# or select rooms
# TODO: choose longest curve to rotate by, also if it's a line - done
# TODO: try using room boundaries for crop, if fails use BBox


def find_crop_box(view):
    with DB.TransactionGroup(revit.doc, "Temp to find crop") as tg:
        tg.Start()
        with DB.Transaction(revit.doc, "temp") as t2:
            t2.Start()
            view.CropBoxVisible = False
            t2.Commit()
            hidden = DB.FilteredElementCollector(revit.doc, view.Id).ToElementIds()
            count_hidden = 0
            t2.Start()
            view.CropBoxVisible = True
            t2.Commit()
            # revit.doc.Regenerate()
            shown = DB.FilteredElementCollector(revit.doc, view.Id).ToElementIds()
            count_shown = 0
            crop_box_el = DB.FilteredElementCollector(revit.doc, view.Id).Excluding(hidden).FirstElement()
            tg.RollBack()
            if crop_box_el:
                return crop_box_el
            else:
                print ("CROP NOT FOUND")
                return None


def degree_conv(x):
    return (x*180)/math.pi


def point_equal_list(pt, lst):
    for el in list(lst):
        if pt.IsAlmostEqualTo(el, 0.003):
            return el
    else:
        return None


def set_anno_crop(v):
    anno_crop = v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
    anno_crop.Set(1)


def get_open_ends(curves_list):
    endpoints = []
    for curve in curves_list:
        for i in range(2):
            duplicate = point_equal_list(curve.GetEndPoint(i), endpoints)
            if duplicate:
                endpoints.remove(duplicate)
            else:
                endpoints.append(curve.GetEndPoint(i))
    if endpoints:
        return endpoints
    else:
        return None


def get_room_bound(r):
    room_boundaries = DB.CurveLoop()
    # get room boundary segments
    room_segments = r.GetBoundarySegments(DB.SpatialElementBoundaryOptions())
    # iterate through loops of segments and add them to the array
    for seg_loop in room_segments:
        curve_loop = [s.GetCurve() for s in seg_loop]
        open_ends = get_open_ends(curve_loop)
        if open_ends:
            print(open_ends)
            return None
        for old_curve in curve_loop:
            room_boundaries.Append(old_curve)
    return room_boundaries


def offset_bbox(bbox, offset):
    """
    Offset Bounding Box by given offset
    http://archi-lab.net/create-view-by-room-with-dynamo/
    """
    bboxMinX = bbox.Min.X - offset
    bboxMinY = bbox.Min.Y - offset
    bboxMinZ = bbox.Min.Z - offset
    bboxMaxX = bbox.Max.X + offset
    bboxMaxY = bbox.Max.Y + offset
    bboxMaxZ = bbox.Max.Z + offset
    newBbox = DB.BoundingBoxXYZ()
    newBbox.Min = DB.XYZ(bboxMinX, bboxMinY, bboxMinZ)
    newBbox.Max = DB.XYZ(bboxMaxX, bboxMaxY, bboxMaxZ)
    return newBbox


titleblock = forms.select_titleblocks(doc=revit.doc)

if not selection:
    forms.alert('You need to select at least one Room.', exitscript=True)


col_view_types = DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType).WhereElementIsElementType()
floor_plan_type = [vt for vt in col_view_types if vt.FamilyName == "Floor Plan"][0]

plan_type = DB.ViewType.FloorPlan
crop_offset = 1
elevation_type = \
[vt for vt in DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType) if vt.FamilyName == "Elevation"][0]
view_scale = 25
sheet_num = "0001"


plan_position = DB.XYZ(0.282, 0.434, 0)
elevations_positions = [DB.XYZ(1.14, 1.25, 0), DB.XYZ(1.805, 1.25, 0), DB.XYZ(1.14, 0.434, 0), DB.XYZ(1.805, 0.434, 0)]


def get_longest_boundary(r):
    bound = r.GetBoundarySegments(DB.SpatialElementBoundaryOptions())
    longest = None
    for loop in bound:
        for b in loop:
            curve = b.GetCurve()
            if curve.Length > longest and isinstance(curve, DB.Line):
                longest = curve
    return longest


for room in selection:

    with revit.Transaction("Create Plan", revit.doc):
        level = room.Level

        # Create Floor Plan
        viewplan = DB.ViewPlan.Create(revit.doc, floor_plan_type.Id, level.Id)
        viewplan.Scale = view_scale
        # choose one longest curve to use as reference for rotation
        longest_boundary = get_longest_boundary(room)
        p = longest_boundary.GetEndPoint(0)
        q = longest_boundary.GetEndPoint(1)
        v = q - p

        bbox_angle = v.AngleTo(DB.XYZ.BasisY)
        # correct angles
        if degree_conv(bbox_angle) > 90:
            bbox_angle = bbox_angle - math.radians(90)
        elif degree_conv(bbox_angle) < 45:
            bbox_angle = - bbox_angle
        else:
            bbox_angle = bbox_angle
        # get viewplan bbox, center
        bbox = room.get_BoundingBox(viewplan)
        center = 0.5 * (bbox.Max + bbox.Min)
        axis = DB.Line.CreateBound(center, center + DB.XYZ.BasisZ)
    # find crop box element (method with transactions)
    crop_box_el = find_crop_box(viewplan)
    print (crop_box_el)


    with revit.Transaction("Rotate Plan", revit.doc):
        rotated = DB.ElementTransformUtils.RotateElement(revit.doc, crop_box_el.Id, axis, bbox_angle)
        viewplan.CropBoxActive = True
        revit.doc.Regenerate()
        new_bbox = room.get_BoundingBox(viewplan)
        viewplan.CropBox = new_bbox

        # todo: set the crop of room to room boundaries
        # if get_room_bound(room):
        #     crop_shape = viewplan.GetCropRegionShapeManager()
        #     crop_shape.SetCropShape(get_room_bound(room))
        # else:
        #     new_bbox = room.get_BoundingBox(viewplan)
        #     viewplan.CropBox = new_bbox

        # Rename Floor Plan
        room_name_nr = room.Number + " - " + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        viewplan_name = room_name_nr + " Plan"
        while helper.get_view(viewplan_name):
            viewplan_name = viewplan_name + " Copy 1"
        viewplan.Name = viewplan_name
        set_anno_crop(viewplan)


        # Create Elevations
        elevations_col = []
        marker_position = room.Location.Point
        new_marker = DB.ElevationMarker.CreateElevationMarker(revit.doc, elevation_type.Id, marker_position, view_scale)
        elevation_count = ["A", "B", "C", "D"]
        for i in range(4):
            elevation = new_marker.CreateElevation(revit.doc, viewplan.Id, i)
            # Rename elevations
            elevation_name = room_name_nr + " - Elevation " + elevation_count[i]
            while helper.get_view(elevation_name):
                elevation_name = elevation_name + " Copy 1"

            elevation.Name = elevation_name
            elevations_col.append(elevation)
            set_anno_crop(elevation)
            print (elevation.BoundingBox)

        # rotate marker
        marker_axis = DB.Line.CreateBound(marker_position, marker_position + DB.XYZ.BasisZ)
        rotated = new_marker.Location.Rotate(marker_axis, bbox_angle)

        sheet = helper.create_sheet(sheet_num, room_name_nr, titleblock)

    with revit.Transaction("Add Views to Sheet", revit.doc):
        place_plan = DB.Viewport.Create(revit.doc, sheet.Id, viewplan.Id, plan_position)
        for i, pos in izip(elevations_col, elevations_positions):
            place_elevation = DB.Viewport.Create(revit.doc, sheet.Id, i.Id, pos)
        print("Sheet : {0} ".format(output.linkify(sheet.Id)))


