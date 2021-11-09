__title__ = "Room Elevations"
__doc__ = "Creates elevation markers and rotates them to align with the room"

from pyrevit import revit, DB, script, forms, HOST_APP
from rpw.ui.forms import (FlexForm, Label, TextBox, Button)
import helper
from pyrevit.revit.db import query
from itertools import izip
from collections import namedtuple
import math
from Autodesk.Revit import Exceptions

# use preselected elements, filtering rooms only
selection = helper.select_rooms_filter()

# DONE: choose longest curve to rotate by, also if it's a line
# DONE: try using room boundaries for crop, if fails use BBox
# DONE: offset boundary curve - done
# DONE: ask for scale and sheet number


if not selection:
    forms.alert('You need to select at least one Room.', exitscript=True)


elevation_type = \
    [vt for vt in DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType) if vt.FamilyName == "Elevation"][0]
view_scale = 25

with revit.Transaction("Create Elevations", revit.doc):
    for room in selection:
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
        # Create Elevations
        elevations_col = []
        marker_position = room.Location.Point
        room_name_nr = room.Number + " - " + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        new_marker = DB.ElevationMarker.CreateElevationMarker(revit.doc, elevation_type.Id, marker_position, view_scale)
        elevation_count = ["A", "B", "C", "D"]
        revit.doc.Regenerate()
        for i in range(4):
            elevation = new_marker.CreateElevation(revit.doc, revit.active_view.Id, i)
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



