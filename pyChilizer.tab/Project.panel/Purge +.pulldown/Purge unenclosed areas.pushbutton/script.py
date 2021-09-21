__title__= "Remove \nUnenclosed Areas"
__doc__ = "Delete unenclosed areas from project"

from pyrevit import revit, DB

# collect
with revit.Transaction("Remove Unenclosed Areas"):
    areas = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_Areas) \
        .WhereElementIsNotElementType() \
        .ToElements()


    # get ids of areas with location and zero area
    unplaced_ids = [a.Id for a in areas if a.Location and a.Area == 0]

    deleted = [] # to keep track of elements deleted

    # remove unplaced areas
    for upid in unplaced_ids:
        revit.doc.Delete(upid)
        deleted.append(upid)

    # print result
    print("Removed {0} unplaced areas".format(len(deleted)))
