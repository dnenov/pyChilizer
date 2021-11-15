__title__= "Remove\nunplaced rooms"
__doc__ = "Delete unplaced rooms from project"

from pyrevit import revit, DB, forms

# collect
rooms = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_Rooms) \
        .WhereElementIsNotElementType() \
        .ToElements()

forms.alert_ifnot(rooms, "No Rooms in model.", exitscript=True)

# get ids of rooms with location equal to None
unplaced_ids = [r.Id for r in rooms if r.Location == None]
forms.alert_ifnot(unplaced_ids, "No unplaced Rooms found, compliments!", exitscript=True)

with revit.Transaction("Remove unplaced rooms"):
    deleted = [] # to keep track of elements deleted
    # remove unplaced rooms
    for upid in unplaced_ids:
        revit.doc.Delete(upid)
        deleted.append(upid)
    # print result
    print("Removed {0} unplaced rooms".format(len(deleted)))
