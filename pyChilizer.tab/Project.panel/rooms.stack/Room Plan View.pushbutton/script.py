__title__ = "Room Plan View"
__doc__ = "Creates room plans"


from pyrevit import revit, DB, script, forms, HOST_APP
from pyrevit.revit.db import query
from pyrevit.framework import List
from rpw.ui.forms import FlexForm, Label, TextBox, Button,ComboBox, Separator
from Autodesk.Revit import Exceptions
from itertools import izip
import math
import helper
import re


output = script.get_output()
logger = script.get_logger()
bound_opt = DB.SpatialElementBoundaryOptions()
# use preselected elements, filtering rooms only
selection = helper.select_rooms_filter()
if not selection:
    forms.alert("You need to select at least one Room.", exitscript=True)

# TODO: try using room boundaries for crop, if fails use BBox, correct the bbox rotation on fail

# collect all view templates for plans
viewplans = DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewPlan) # collect plans
viewplan_dict = {v.Name: v for v in viewplans if v.IsTemplate} # only fetch IsTemplate plans
# add none as an option
viewplan_dict["<None>"] = None


# collect and take the first view plan type, elevation type, set default scale
col_view_types = (DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType).WhereElementIsElementType())
floor_plan_type = [vt for vt in col_view_types if vt.FamilyName == "Floor Plan"][0]
view_scale = 50

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
    Label("View Template for Plans"),
    ComboBox(name="vt_plans", options=sorted(viewplan_dict), default="<None>"),
    Separator(),
    Button("Select"),
]

form = FlexForm("View Settings", components)
form.show()
# match the variables with user input
chosen_vt_plan = viewplan_dict[form.values["vt_plans"]]
chosen_crop_offset = helper.correct_input_units(form.values["crop_offset"])


for room in selection:
    with revit.Transaction("Create Plan", revit.doc):
        level = room.Level
        room_location = room.Location.Point
        # Create Floor Plan
        viewplan = DB.ViewPlan.Create(revit.doc, floor_plan_type.Id, level.Id)
        viewplan.Scale = view_scale

    # find crop box element (method with transactions, must be outside transaction)
    crop_box_el = helper.find_crop_box(viewplan)

    with revit.Transaction("Rotate Plan", revit.doc):
        # rotate the view plan along the room's longest boundary
        axis = helper.get_bb_axis_in_view(room, viewplan)
        angle = helper.room_rotation_angle(room)
        rotated = DB.ElementTransformUtils.RotateElement(
            revit.doc, crop_box_el.Id, axis, angle
        )
        viewplan.CropBoxActive = True
        revit.doc.Regenerate()

        room_boundaries = helper.get_room_bound(room)
        if room_boundaries:
            # try offsetting boundaries (to include walls in plan view)
            try:
                offset_boundaries = room_boundaries.CreateViaOffset(
                    room_boundaries, chosen_crop_offset, DB.XYZ(0, 0, 1)
                )
                crop_shape = viewplan.GetCropRegionShapeManager()
                crop_shape.SetCropShape(offset_boundaries)
                revit.doc.Regenerate()
            # for some shapes the offset will fail, then use BBox method
            except:
                revit.doc.Regenerate()
                # room bbox in this view
                new_bbox = room.get_BoundingBox(viewplan)
                viewplan.CropBox = new_bbox
                # this part corrects the rotation of the BBox

                tr_left = DB.Transform.CreateRotationAtPoint(DB.XYZ.BasisZ, angle, room_location)
                # tr_right = DB.Transform.CreateRotationAtPoint(DB.XYZ.BasisZ, -angle, room_location)
                tr_right = tr_left.Inverse

                rotate_left = helper.get_aligned_crop(room.ClosedShell, tr_left)
                rotate_right = helper.get_aligned_crop(room.ClosedShell, tr_right)

                aligned_crop_loop = rotate_right


                crsm = viewplan.GetCropRegionShapeManager()
                curve_loop_offset = DB.CurveLoop.CreateViaOffset(aligned_crop_loop, chosen_crop_offset, DB.XYZ.BasisZ)
                crsm.SetCropShape(aligned_crop_loop)

        # Rename Floor Plan
        room_name_nr = (
                room.Number
                + " - "
                + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        )
        viewplan_name = room_name_nr + " Plan"
        while helper.get_view(viewplan_name):
            viewplan_name = viewplan_name + " Copy 1"
        viewplan.Name = viewplan_name
        helper.set_anno_crop(viewplan)
        helper.apply_vt(viewplan, chosen_vt_plan)

        print("Created Plan {0} \t for Room {1} ".format(output.linkify(viewplan.Id), room_name_nr))
