from pyrevit import revit, DB, script, forms
from rpw.ui.forms import FlexForm, Label, TextBox, Button,ComboBox, Separator
from pychilizer import database, units, select, geo
import sys
from Autodesk.Revit import Exceptions

output = script.get_output()
logger = script.get_logger()

selection = select.select_with_cat_filter(DB.BuiltInCategory.OST_Rooms, "Pick Rooms for Room Data Sheets")
doc = __revit__.ActiveUIDocument.Document

# collect all view templates sections
viewsections = DB.FilteredElementCollector(revit.doc).OfClass(DB.ViewSection) # collect sections
viewsection_dict = {v.Name: v for v in viewsections if v.IsTemplate} # only fetch the IsTemplate sections

# add none as an option
viewsection_dict["<None>"] = None


# collect and take the first elevation type, set default scale
elevation_type = database.get_view_family_types(DB.ViewFamily.Elevation, doc)[0]
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
    Separator(),
    Button("Select"),
]

form = FlexForm("View Settings", components)
ok = form.show()
if ok:
    # match the variables with user input
    chosen_vt_elevation = viewsection_dict[form.values["vt_elevs"]]
    chosen_crop_offset = units.correct_input_units(form.values["crop_offset"], doc)
else:
    sys.exit()

for room in selection:
    with revit.Transaction("Create Elevations", doc):
        room_location = room.Location.Point
        # rotate the view plan along the room's longest boundary
        axis = geo.get_bb_axis_in_view(room, viewplan)
        angle = geo.room_rotation_angle(room)

        # Format View Name
        room_name_nr = (
                room.Number
                + " - "
                + room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        )

        # Create Elevations
        doc.Regenerate()
        elevations_col = []
        new_marker = DB.ElevationMarker.CreateElevationMarker(
            doc, elevation_type.Id, room_location, view_scale
        )
        elevation_count = ["A", "B", "C", "D"]
        doc.Regenerate()
        for i in range(4):
            try:
                elevation = new_marker.CreateElevation(doc, viewplan.Id, i)
            except Exceptions.ArgumentException:

                forms.alert(msg="Something is wrong with the marker", \
                            sub_msg="Please check the Elevation Tag and Elevation Marker Families are working properly.", \
                            ok=True, \
                            warn_icon=True, exitscript=True)

            elevation.Scale = view_scale
            # Rename elevations
            elevation_name = room_name_nr + " - Elevation " + elevation_count[i]
            while database.get_view(elevation_name, doc):
                elevation_name = elevation_name + " Copy 1"

            elevation.Name = elevation_name
            elevations_col.append(elevation)
            database.set_anno_crop(elevation)

        # rotate marker
        doc.Regenerate()
        marker_axis = DB.Line.CreateBound(
            room_location, room_location + DB.XYZ.BasisZ
        )
        rotated = new_marker.Location.Rotate(marker_axis, angle)
        doc.Regenerate()
        print("Created Elevations for room {}".format(room_name_nr))

        for el in elevations_col:
            room_bb = room.get_BoundingBox(el)
            geo.set_crop_to_bb(room, el, crop_offset=chosen_crop_offset)
            database.apply_vt(el, chosen_vt_elevation)
            print ("\n{}".format(output.linkify(el.Id)))