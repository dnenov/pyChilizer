__title__= "Remove \nUnplaced Rooms"
__doc__ = "Delete unplaced rooms from project"

from pyrevit import revit, DB

# collect
with revit.Transaction("Remove Unplaced Rooms"):
    rooms = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_Rooms) \
        .WhereElementIsNotElementType() \
        .ToElements()

    # get ids of rooms with location equal to None
    unplaced_ids = [r.Id for r in rooms if r.Location == None]

    deleted = [] # to keep track of elements deleted

    # remove unplaced rooms
    for upid in unplaced_ids:
        revit.doc.Delete(upid)
        deleted.append(upid)

    # print result
    print("Removed {0} unplaced rooms".format(len(deleted)))
