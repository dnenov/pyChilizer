from pyrevit import revit, DB, script, forms, HOST_APP
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
import math


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


def get_orientation_by_normal(normal):
    # use a normal to get str conveying orientation (N/S/E/W/NE/NW/SE/SW)

    # rotate normal taking into account True North rotation
    rotated_normal = rotate_vector(normal, -(get_true_north_angle()))
    # get degrees to X and Y axis
    angle_x = math.degrees(rotated_normal.AngleTo(DB.XYZ(1, 0, 0)))
    angle_y = math.degrees(rotated_normal.AngleTo(DB.XYZ(0, 1, 0)))
#    print("Function \n Angle to X: {} \n Angle to Y:{}".format(angle_x, angle_y))
    orientation = None
    # sort orientation using degrees to X and Y
    if 10 < angle_x < 80 and 10 < angle_y < 80:
        orientation = "North East"

    elif angle_x > 100 and 10 < angle_y < 80:
        orientation = "North West"

    elif angle_x > 100 and angle_y > 100:
        orientation = "South West"

    elif 10 < angle_x < 80 and angle_y > 100:
        orientation = "South East"

    elif angle_x >= 100 and 80 <= angle_y <= 100:
        orientation = "West"

    elif 80 <= angle_x <= 100 and angle_y >= 100:
        orientation = "South"

    elif angle_x <= 10 and 80 <= angle_y <= 100:
        orientation = "East"

    elif 80 <= angle_x <= 100 and angle_y <= 10:
        orientation = "North"

    else:
        orientation = "Blank"
    return orientation


# gather windows
coll_windows = DB.FilteredElementCollector(revit.doc).OfCategory(
    DB.BuiltInCategory.OST_Windows).WhereElementIsNotElementType().ToElements()

win_parameter_set = coll_windows[0].Parameters
win_params_text = [p for p in win_parameter_set if p.StorageType.ToString() == "String" and p.Definition.VariesAcrossGroups]
win_params_text.append(coll_windows[0].get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK))

win_dict1 = {p.Definition.Name: p for p in win_params_text}
# construct rwp UI
components = [
    Label("Which Windows parameter to populate:\n Must Vary across groups"),
    ComboBox(name="win_combobox1", options=win_dict1),
    Button("Select")]
form = FlexForm("Pick Parameter", components)
form.show()
# assign chosen parameters
chosen_win_param = form.values["win_combobox1"]

with revit.Transaction("Windows Orientation"):
    for window in coll_windows:
        host_wall = window.Host
        if host_wall:

            wall_face_ref = DB.HostObjectUtils.GetSideFaces(host_wall, DB.ShellLayerType.Exterior)[0]
            ext_side = revit.doc.GetElement(wall_face_ref).GetGeometryObjectFromReference(wall_face_ref)
            if isinstance(ext_side, DB.PlanarFace):
                normal_to_wall = ext_side.FaceNormal.Normalize()
                window_orientation = get_orientation_by_normal(normal_to_wall)

                # TODO: chaned this ugly bit
                if chosen_win_param.Definition.Name == "Mark":
                    change = window.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK).Set(str(window_orientation))
                else:
                    change = window.get_Parameter(chosen_win_param.GUID).Set(str(window_orientation))
