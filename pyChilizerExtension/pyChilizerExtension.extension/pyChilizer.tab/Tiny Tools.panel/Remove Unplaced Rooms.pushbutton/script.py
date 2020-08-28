__title__= "Remove \nUnplaced Rooms"
__doc__ = "Delete unplaced rooms from project"

# pylint: disable=invalid-name,import-error,superfluous-parens

from pyrevit import revit, DB
from pyrevit import script
from pyrevit import framework

output = script.get_output()

# collect
with revit.Transaction("Remove Unplaced Rooms"):
    rooms = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_Rooms) \
        .WhereElementIsNotElementType() \
        .ToElements()

    unplaced_ids = []
    for r in rooms:
        room_areas = r.Parameter[DB.BuiltInParameter.ROOM_AREA]
        if room_areas.AsDouble() == 0:
            unplaced_ids.append(r.Id)

    # remove
    revit.doc.Delete(framework.List[DB.ElementId](unplaced_ids))
