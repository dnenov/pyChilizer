__title__ = "Room Elevations"
__doc__ = "Creates elevation markers and rotates them to align with the room"

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
logger = script.get_logger()
bound_opt = DB.SpatialElementBoundaryOptions()
# use preselected elements, filtering rooms only
selection = helper.select_rooms_filter()
if not selection:
    forms.alert("You need to select at least one Room.", exitscript=True)


# collect all view templates for plans and sections
viewsections = DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewSection) # collect sections
viewsection_dict = {v.Name: v for v in viewsections if v.IsTemplate} # only fetch the IsTemplate sections

# add none as an option
viewsection_dict["<None>"] = None


# collect and take the first elevation type, set default scale
elevation_type = [vt for vt in DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType) if vt.FamilyName == "Elevation"][0]
view_scale = 50
viewplan = revit.active_view
# get units for Crop Offset variable
display_units = DB.Document.GetUnits(revit.doc).GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
if helper.is_metric(revit.doc):
    unit_sym = "Crop Offset [mm]"
    default_crop_offset = 350
else:
    unit_sym = "Crop Offset [decimal inches]"
    default_crop_offset = 9.0

components = [
    Label(unit_sym),
    TextBox("crop_offset", Text=str(default_crop_offset)),
    Label("View Template for Elevations"),
    ComboBox(name="vt_elevs", options=sorted(viewsection_dict), default="<None>"),
    Separator(),
    Button("Select"),
]

form = FlexForm("View Settings", components)
form.show()
# match the variables with user input
chosen_vt_elevation = viewsection_dict[form.values["vt_elevs"]]
chosen_crop_offset = helper.correct_input_units(form.values["crop_offset"])


for room in selection:
    with revit.Transaction("Create Elevations", revit.doc):
        room_location = room.Location.Point
        # rotate the view plan along the room's longest boundary
        axis = helper.get_bb_axis_in_view(room, viewplan)
        angle = helper.room_rotation_angle(room)

        # Format View Name
        room_name_nr = (
                room.Number
                + " - "
                + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        )

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
        print("Created Elevations for room {}".format(room_name_nr))

        for el in elevations_col:
            room_bb = room.get_BoundingBox(el)
            helper.set_crop_to_bb(room, el, crop_offset=chosen_crop_offset)
            helper.apply_vt(el, chosen_vt_elevation)
            print ("\n{}".format(output.linkify(el.Id)))