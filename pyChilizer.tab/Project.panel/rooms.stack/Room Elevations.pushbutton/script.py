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
viewplan = revit.active_view

if not selection:
    forms.alert('You need to select at least one Room.', exitscript=True)

elevation_type = \
    [vt for vt in DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType) if vt.FamilyName == "Elevation"][0]
view_scale = 25

with revit.Transaction("Create Elevations", revit.doc):
    for room in selection:
        room_location = room.Location.Point
        angle = helper.room_rotation_angle(room)
        room_name_nr = (
                room.Number
                + " - "
                + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        )

        # Create Elevations
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
            helper.set_crop_to_bb(room, elevation, 1)

        # rotate marker
        revit.doc.Regenerate()
        marker_axis = DB.Line.CreateBound(
            room_location, room_location + DB.XYZ.BasisZ
        )
        rotated = new_marker.Location.Rotate(marker_axis, angle)
        revit.doc.Regenerate()



