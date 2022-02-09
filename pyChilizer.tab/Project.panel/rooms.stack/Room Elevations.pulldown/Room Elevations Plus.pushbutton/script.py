from pyrevit import revit, DB, script, forms
from pyrevit.revit import selection as sel
from rpw.ui.forms import FlexForm, Label, TextBox, Button, ComboBox, Separator
from pychilizer import database, units, select, geo
import sys
from pyrevit.framework import List
from System.Collections.Generic import IList
import clr
from Autodesk.Revit import Exceptions

# clr.Reference[IList[DB.ClosestPointsPairBetweenTwoCurves]]

output = script.get_output()
logger = script.get_logger()

# use preselected elements, filtering rooms only
room = sel.pick_element_by_category(cat_name_or_builtin=DB.BuiltInCategory.OST_Rooms)
if not room:
    forms.alert("You need to select one Room.", exitscript=True)

# collect all view templates sections
viewsections = DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewSection)  # collect sections
viewsection_dict = {v.Name: v for v in viewsections if v.IsTemplate}  # only fetch the IsTemplate sections

# add none as an option
viewsection_dict["<None>"] = None

# collect and take the first elevation type, set default scale
elevation_type = [vt for vt in DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType) if
                  database.get_name(vt) in ["Interior Elevation", "Internal Elevation"]][0]
section_type = [vt for vt in DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewFamilyType) if
                database.get_name(vt) == "Building Section"][0]

tolerance = 0.032
view_scale = 50
viewplan = revit.active_view
# get units for Crop Offset variable
if units.is_metric(revit.doc):
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
    Label("Use Sections or Elevations"),
    ComboBox(name="sec_or_elev", options=(["Sections", "Elevations"])),
    Separator(),
    Button("Select"),
]

form = FlexForm("View Settings", components)
ok = form.show()
if ok:
    # match the variables with user input
    chosen_vt_elevation = viewsection_dict[form.values["vt_elevs"]]
    chosen_crop_offset = units.correct_input_units(form.values["crop_offset"])
else:
    sys.exit()

with revit.Transaction("Create Elevations", revit.doc):
    # room_location = room.Location.Point
    # rotate the view plan along the room's longest boundary
    # axis = geo.get_bb_axis_in_view(room, viewplan)
    # angle = geo.room_rotation_angle(room)

    # Format View Name
    room_name_nr = (
            room.Number
            + " - "
            + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
    )

    boundaries = geo.get_room_bound(room)

    # get unique boundaries by sorting lines
    axis_set = []
    bound_curves = []
    for curve in boundaries:

        deriv = curve.ComputeDerivatives(0.5, True)
        tangent = deriv.BasisX
        pt = curve.Evaluate(0.5, True)
        # print (pt)
        axis = DB.Line.CreateUnbound(pt, tangent)
        on_axis = False
        if not axis_set:
            # print ("First")
            axis_set.append(axis)
            bound_curves.append(curve)
        for line in axis_set:
            distance = line.Distance(pt)
            # print (distance)
            if distance <= tolerance:
                # print ("on axis")
                on_axis = True
        if not on_axis:
            axis_set.append(axis)
            bound_curves.append(curve)
    print("Nr Lines {}".format(len(axis_set)))



    # try first with lines that you got
    for border in bound_curves:
        # determine section box (building coder)
        p = border.GetEndPoint(0)
        q = border.GetEndPoint(1)
        v = q - p

        w = v.GetLength()
        bb = room.get_BoundingBox(None)
        minZ = bb.Min.Z
        maxZ = bb.Max.Z
        h = maxZ - minZ
        offset = 0.2 * w

        min = DB.XYZ(-w, minZ - offset, -offset)
        max = DB.XYZ(w, maxZ + offset, 0)

        midpoint = p + 0.5 * v
        direction = v.Normalize()
        up = DB.XYZ.BasisZ
        view_direction = direction.CrossProduct(up)

        t = DB.Transform.Identity
        t.Origin = midpoint
        t.BasisX = direction
        t.BasisY = up
        t.BasisZ = view_direction

        section_box = DB.BoundingBoxXYZ()
        section_box.Transform = t
        section_box.Min = min
        section_box.Max = max

        new_section = DB.ViewSection.CreateSection(revit.doc, section_type.Id, section_box)

    # if form.values["sec_or_elev"] == "Elevations":
    #     # Create Elevations
    #     elevations_col = []
    #     new_marker = DB.ElevationMarker.CreateElevationMarker(
    #         revit.doc, elevation_type.Id, room_location, view_scale
    #     )
    #     elevation_count = ["A", "B", "C", "D"]
    #     revit.doc.Regenerate()
    #     for i in range(4):
    #         elevation = new_marker.CreateElevation(revit.doc, viewplan.Id, i)
    #         elevation.Scale = view_scale
    #         # Rename elevations
    #         elevation_name = room_name_nr + " - Elevation " + elevation_count[i]
    #         while database.get_view(elevation_name):
    #             elevation_name = elevation_name + " Copy 1"
    #
    #         elevation.Name = elevation_name
    #         elevations_col.append(elevation)
    #         database.set_anno_crop(elevation)
    #
    #     # rotate marker
    #     revit.doc.Regenerate()
    #     marker_axis = DB.Line.CreateBound(
    #         room_location, room_location + DB.XYZ.BasisZ
    #     )
    #     rotated = new_marker.Location.Rotate(marker_axis, angle)
    #     revit.doc.Regenerate()
    #     print("Created Elevations for room {}".format(room_name_nr))
    #
    #     for el in elevations_col:
    #         room_bb = room.get_BoundingBox(el)
    #         geo.set_crop_to_bb(room, el, crop_offset=chosen_crop_offset)
    #         database.apply_vt(el, chosen_vt_elevation)
    #         print("\n{}".format(output.linkify(el.Id)))
    # else:
    #     # create sections
    #     pass
