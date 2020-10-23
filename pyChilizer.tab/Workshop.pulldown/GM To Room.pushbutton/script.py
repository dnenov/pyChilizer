__title__ = "GM to Rooms"
__doc__ = "Place rooms in the location of the generic model units"


from itertools import izip
from pyrevit import revit, DB, script, forms
import clr

from time import time

# Gather GM
coll_gm = DB.FilteredElementCollector(revit.doc) \
    .OfCategory(DB.BuiltInCategory.OST_GenericModel) \
    .WhereElementIsNotElementType() \
    .ToElements()

# TODO: filter housing units only

# Pick which parameters to copy
parameters_names_list = []
for g in coll_gm:

    element_parameter_set = g.Parameters
    for p in element_parameter_set:
        parameter_name = p.Definition.Name
        if parameter_name not in parameters_names_list:
            parameters_names_list.append(parameter_name)

#parameters_names_list.sort()
#sel_parameter = forms.SelectFromList.show(parameters_names_list
#                                                , button_name="Select Parameters"
#                                                , multiselect=False)

# Place rooms
with revit.Transaction('Place Room', log_errors=False):
    for gm in coll_gm:
        level = revit.doc.GetElement(gm.LevelId)
        # get Bounding Box of generic model element
        bb = gm.get_BoundingBox(None)
        # get the center of Bounding Box
        center_bb = (bb.Max + bb.Min)/2

        # specify UV
        u = center_bb.X
        v = center_bb.Y
        uv = DB.UV(u, v)

        # place room on level and UV
        room = revit.doc.Create.NewRoom(level, uv)

        # set room names to GM type name
        try:
            room_name = room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).Set(gm.Name)
        finally:
            pass



