from pyrevit import revit, DB, script, forms
from rpw.ui.forms import FlexForm, Label, Button, ComboBox, TextBox, Separator
from pychilizer import database, units, select, geo
import sys
from Autodesk.Revit import Exceptions
import roomelevationsplusui as ui


output = script.get_output()
logger = script.get_logger()
MINIMAL_LENGTH = 1.5
ELEVATION_SPACING = 0.3
ELEVATION_ID = 0
doc = __revit__.ActiveUIDocument.Document
active_view = revit.active_view
active_view_scale = active_view.Scale

selection = select.select_with_cat_filter(DB.BuiltInCategory.OST_Rooms, "Pick Rooms for Room Data Sheets")

# collect all view templates sections
viewsections = DB.FilteredElementCollector(doc).OfClass(DB.ViewSection)  # collect sections
viewsection_dict = {v.Name: v for v in viewsections if v.IsTemplate}  # only fetch the IsTemplate sections

# add none as an option
viewsection_dict["<None>"] = None

# collect and take the first elevation type, set default scale
elevation_type = database.get_view_family_types(DB.ViewFamily.Elevation, doc)[0]
section_type = database.get_view_family_types(DB.ViewFamily.Section, doc)[0]

# tolerance = 0.032
VIEW_SCALE = 50
# get units for Crop Offset variable
if units.is_metric(doc):
    unit_sym = "[mm]"
    default_crop_offset = 350
else:
    unit_sym = "Crop Offset [decimal inches]"
    default_crop_offset = 9.0

components = [
    Label("Elevation Crop Offset" +unit_sym),
    TextBox("crop_offset", Text=str(default_crop_offset)),
    Label("View Template for Elevations"),
    ComboBox(name="vt_elevs", options=sorted(viewsection_dict), default="<None>"),
    Label("Use Sections or Elevations"),
    ComboBox(name="sec_or_elev", options=(["Sections", "Elevations"])),
    Label("Elevation Marker offset from boundary" + unit_sym),
    TextBox("marker_offset", Text=str(300)),
    Separator(),
    Button("Select"),
]

form = FlexForm("View Settings", components)
ok = form.show()
if ok:
    chosen_vt_elevation = viewsection_dict[form.values["vt_elevs"]]
    # match the variables with user input
    chosen_crop_offset = units.correct_input_units(form.values["crop_offset"], doc)
    chosen_marker_offset = units.correct_input_units(form.values["marker_offset"], doc)

else:
    sys.exit()


with revit.Transaction("Create Room Sections", doc):
    for room in selection:
        # Format View Name
        room_name_nr = (
                room.Number
                + " - "
                + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        )

        boundaries = geo.discard_short(geo.get_room_bound(room), MINIMAL_LENGTH)
        boundaries = [curve for curve in boundaries if isinstance(curve, DB.Line)]
        # get unique boundaries by sorting lines
        # bound_curves = geo.get_unique_borders(boundaries, tolerance)
        elevation_labels = database.get_alphabetic_labels(len(boundaries))
        print("Created Elevations for room {}".format(room_name_nr))

        counter = 0
        for boundary in boundaries:
            # section name
            elevation_name = room_name_nr + " - Elevation " + elevation_labels[counter]
            counter += 1
            while database.get_view(elevation_name, doc):
                elevation_name = elevation_name + " Copy 1"

            # create a bbox parallel to the border
            sb = database.create_parallel_bbox(boundary, room)

            if form.values["sec_or_elev"] == "Sections":
                # for room elevations as sections
                new_room_elevation = DB.ViewSection.CreateSection(doc, section_type.Id, sb)
            else:
                # for room elevations as elevations
                # temporarily switch to smaller scale - better results rotating elevations to face the boundary
                active_view.Scale = 10

                # elevation marker position - middle of the boundary
                boundary_center = boundary.Evaluate(0.5, True)

                # offset inwards and check if it's the right side (check if inside room)
                marker_position = geo.offset_curve_inwards_into_room(boundary,
                                                                     room,
                                                                     chosen_marker_offset)\
                    .Evaluate(0.5, True)

                # create marker
                new_marker = DB.ElevationMarker.CreateElevationMarker(doc, elevation_type.Id, marker_position, VIEW_SCALE)

                # create 1 elevation
                try:
                    new_room_elevation = new_marker.CreateElevation(doc, active_view.Id, ELEVATION_ID)

                except Exceptions.ArgumentException:
                    forms.alert("Elevation Marker is invalid. Please review the Elevation Marker and retry",
                                exitscript=True)

                # rotate the marker to face the boundary
                geo.orient_elevation_to_line(doc, new_marker, marker_position, boundary, ELEVATION_ID, active_view)

            new_room_elevation.Name = elevation_name
            database.apply_vt(new_room_elevation, chosen_vt_elevation)
            doc.Regenerate()
            geo.set_crop_to_boundary(room, boundary, new_room_elevation, chosen_crop_offset, doc)

            print("\n{}".format(output.linkify(new_room_elevation.Id)))

    active_view.Scale = active_view_scale