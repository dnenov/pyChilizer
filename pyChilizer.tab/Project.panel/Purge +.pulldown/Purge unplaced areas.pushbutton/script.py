__title__ = "Remove\nunplaced areas"
__doc__ = "Delete unplaced areas from project"

from pyrevit import revit, DB, forms

# collect
areas = DB.FilteredElementCollector(revit.doc) \
    .OfCategory(DB.BuiltInCategory.OST_Areas) \
    .WhereElementIsNotElementType() \
    .ToElements()

forms.alert_ifnot(areas, "No Areas in model.", exitscript=True)
# get ids of rooms with location equal to None
unplaced_ids = [a.Id for a in areas if a.Location is None]

forms.alert_ifnot(unplaced_ids, "No unplaced Areas found, well done!", exitscript=True)

with revit.Transaction("Remove Unplaced Areas"):
    deleted = []  # to keep track of elements deleted

    # remove unplaced rooms
    for upid in unplaced_ids:
        revit.doc.Delete(upid)
        deleted.append(upid)

    # print result
    print("Removed {0} unplaced areas".format(len(deleted)))
