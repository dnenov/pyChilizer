__title__= "Remove \nUnplaced Areas"
__doc__ = "Delete unplaced areas from project"

from pyrevit import revit, DB

# collect
with revit.Transaction("Remove Unplaced Areas"):
    areas = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_Areas) \
        .WhereElementIsNotElementType() \
        .ToElements()

    # get ids of rooms with location equal to None
    unplaced_ids = [a.Id for a in areas if a.Location == None]

    deleted = [] # to keep track of elements deleted

    # remove unplaced rooms
    for upid in unplaced_ids:
        revit.doc.Delete(upid)
        deleted.append(upid)

    # print result
    print("Removed {0} unplaced areas".format(len(deleted)))
