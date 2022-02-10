import math

from pyrevit import revit, DB, script, forms
from pyrevit.revit import selection as sel, geom
from rpw.ui.forms import FlexForm, Label, TextBox, Button, ComboBox, Separator
from pychilizer import database, units, select, geo
import sys


output = script.get_output()
logger = script.get_logger()

selection = select.select_rooms_filter()
if not selection:
    forms.alert("You need to select at least one Room.", exitscript=True)

# collect all view templates sections
viewsections = DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewSection)  # collect sections
viewsection_dict = {v.Name: v for v in viewsections if v.IsTemplate}  # only fetch the IsTemplate sections

# add none as an option
viewsection_dict["<None>"] = None

# collect and take the first elevation type, set default scale
elevation_type = database.get_view_family_types(DB.ViewFamily.Elevation)[0]
section_type = database.get_view_family_types(DB.ViewFamily.Section)[0]

tolerance = 0.032
view_scale = 50
# get units for Crop Offset variable
if units.is_metric(revit.doc):
    unit_sym = "Crop Offset [mm]"
    default_crop_offset = 350
else:
    unit_sym = "Crop Offset [decimal inches]"
    default_crop_offset = 9.0

components = [
    # Label(unit_sym),
    # TextBox("crop_offset", Text=str(default_crop_offset)),
    Label("View Template for Elevations"),
    ComboBox(name="vt_elevs", options=sorted(viewsection_dict), default="<None>"),
    # Label("Use Sections or Elevations"),
    # ComboBox(name="sec_or_elev", options=(["Sections", "Elevations"])),
    Separator(),
    Button("Select"),
]

form = FlexForm("View Settings", components)
ok = form.show()
if ok:
    # match the variables with user input
    chosen_vt_elevation = viewsection_dict[form.values["vt_elevs"]]
    # chosen_crop_offset = units.correct_input_units(form.values["crop_offset"])
else:
    sys.exit()


with revit.Transaction("Create Room Sections", revit.doc):
    for room in selection:
        # Format View Name
        room_name_nr = (
                room.Number
                + " - "
                + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        )

        boundaries = geo.discard_short(geo.get_room_bound(room))
        boundaries = [curve for curve in boundaries if isinstance(curve, DB.Line)]
        # get unique boundaries by sorting lines
        bound_curves = geo.get_unique_borders(boundaries, tolerance)

        print("Created Elevations for room {}".format(room_name_nr))

        counter = 0
        for border in bound_curves:
            # section name
            section_name = room_name_nr + " - Elevation " + database.char_i(counter)
            counter += 1
            while database.get_view(section_name):
                section_name = section_name + " Copy 1"

            # create a bbox parallel to the border
            sb = database.create_parallel_bbox(border, room)

            # if form.values["sec_or_elev"] == "Sections":
            new_section = DB.ViewSection.CreateSection(revit.doc, section_type.Id, sb)
            new_section.Name = section_name
            database.apply_vt(new_section, chosen_vt_elevation)
            print("\n{}".format(output.linkify(new_section.Id)))
            # todo: set crop no working
            # set_crop_to_bb(room, new_section, chosen_crop_offset)


            # TODO: Marker rotation not solved yet
            # else:
            # # Create Elevations
            #     new_marker = DB.ElevationMarker.CreateElevationMarker(
            #             revit.doc, elevation_type.Id, marker_pt, view_scale
            #         )
            #     revit.doc.Regenerate()
            #     new_elevation = new_marker.CreateElevation(revit.doc, viewplan.Id, 1)
            #     new_elevation.Name = elev_name
            #     revit.doc.Regenerate()
            #
            #     #debug
            #     view_direction = new_elevation.ViewDirection
            #
            #
            #     marker_axis = DB.Line.CreateBound(marker_pt, marker_pt + DB.XYZ.BasisZ)
            #
            #     p = border.GetEndPoint(0)
            #     q = border.GetEndPoint(1)
            #     v = q - p
            #
            #     angle_to_y = v.AngleTo(view_direction)
            #     angle = angle_to_y - math.radians(90)
            #     if angle < 0:
            #         angle = angle + math.radians(360)
            #     # print ("angle to vd", math.degrees(angle))
            #
            #     # print ("{}\nangle: {}\ncorrected:{}".format(elev_name, math.degrees(angle_to_y), math.degrees(angle)))
            #     rotated_marker = new_marker.Location.Rotate(marker_axis, -(angle))
