__title__ = "Rooms \nOrientation"
__doc__ = "Populate room parameter with values for Single and Double aspect units. Only for last phase. Links not available yet. "

from pyrevit import revit, DB, script, forms, HOST_APP
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
import math
from collections import Counter

rooms = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_Rooms)
windows = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_Windows).WhereElementIsNotElementType()


#TODO: input phase from UI
doc_phases = revit.doc.Phases
last_phase = doc_phases[doc_phases.Size -1]


def count_unique (lst):
    return len(Counter(lst).keys())


def get_true_north_angle():
    # get project's angle to True North
    pbp = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_ProjectBasePoint).FirstElement()
    angle_north = pbp.get_Parameter(DB.BuiltInParameter.BASEPOINT_ANGLETON_PARAM).AsDouble()
    return angle_north


def rotate_vector(vector, angle):
    # rotate vector around Z axis by given angle
    rotation = DB.Transform.CreateRotation(DB.XYZ.BasisZ, angle)
    rotated_vector = rotation.OfVector(vector)
    return rotated_vector


def win_room (elem, phase):
    # get rooms for windows
    if elem.FromRoom[phase]:
        return elem.FromRoom[phase]
    elif elem.ToRoom[phase]:
        return elem.ToRoom[phase]
    else:
        return None


def get_orientation_by_normal(normal):
    # use a normal to get str conveying orientation (N/S/E/W/NE/NW/SE/SW)

    # rotate normal taking into account True North rotation
    rotated_normal = rotate_vector(normal, -(get_true_north_angle()))
    # get degrees to X and Y axis
    angle_x = math.degrees(rotated_normal.AngleTo(DB.XYZ(1, 0, 0)))
    angle_y = math.degrees(rotated_normal.AngleTo(DB.XYZ(0, 1, 0)))

    orientation = None
    # sort orientation using degrees to X and Y
    if 10 < angle_x < 80 and 10 < angle_y < 80:
        orientation = "NE"

    elif angle_x > 100 and 10 < angle_y < 80:
        orientation = "NW"

    elif angle_x > 100 and angle_y > 100:
        orientation = "SW"

    elif 10 < angle_x < 80 and angle_y > 100:
        orientation = "SE"

    elif angle_x >= 100 and 80 <= angle_y <= 100:
        orientation = "WW"

    elif 80 <= angle_x <= 100 and angle_y >= 100:
        orientation = "SS"

    elif angle_x <= 10 and 80 <= angle_y <= 100:
        orientation = "EE"

    elif 80 <= angle_x <= 100 and angle_y <= 10:
        orientation = "NN"

    else:
        orientation = "Blank"
    return orientation


def win_orientation (window1):
    host_wall = window1.Host
    wall_face_ref = DB.HostObjectUtils.GetSideFaces(host_wall, DB.ShellLayerType.Exterior)[0]
    ext_side = revit.doc.GetElement(wall_face_ref).GetGeometryObjectFromReference(wall_face_ref)
    normal_to_wall = ext_side.FaceNormal.Normalize()
    window_orientation = get_orientation_by_normal(normal_to_wall)
    return  window_orientation


# UI - pick which parameter to populate, TODO: which phase to look at
a_room = DB.FilteredElementCollector(revit.doc).OfCategory(
    DB.BuiltInCategory.OST_Rooms).FirstElement()

rm_parameter_set = a_room.Parameters
rm_params_text = [p.Definition.Name for p in rm_parameter_set if p.StorageType.ToString() == "String" and p.Definition.VariesAcrossGroups]

# construct rwp UI
components = [
    Label("Which Rooms parameter to populate:"),
    ComboBox(name="rm_combobox1", options=rm_params_text),
    Button("Select")]
form = FlexForm("Pick Parameter", components)
form.show()
# assign chosen parameters
chosen_room_param = form.values["rm_combobox1"]

# collect orientation of windows by room
orient_dict = {}
for window in windows:
    room = win_room(window, last_phase)
    if room:
        orientation = win_orientation(window)
        if room.Id in orient_dict:
            orient_dict[room.Id].append(orientation)
        else:
            orient_dict[room.Id]=[orientation]

# write room parameter value
with revit.Transaction("Room Orientation"):

    for rm_id in orient_dict.keys():
        sides = count_unique(orient_dict[rm_id])
        rm_param = revit.doc.GetElement(rm_id).LookupParameter(chosen_room_param)
        if sides == 1:
            rm_param.Set("Single")
        elif sides == 2:
            rm_param.Set("Double")
        elif sides >= 3:
            rm_param.Set("Multi")
        else:
            pass


