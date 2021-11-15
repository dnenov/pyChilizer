__title__= "Remove\nunenclosed areas"
__doc__ = "Delete unenclosed areas from project"

from pyrevit import revit, DB, forms

# collect
areas = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_Areas) \
        .WhereElementIsNotElementType() \
        .ToElements()

forms.alert_ifnot(areas, "No Areas in model.", exitscript=True)

# get ids of areas with location and zero area
unenclosed_ids = [a.Id for a in areas if a.Location and a.Area == 0]

forms.alert_ifnot(unenclosed_ids, "All Areas are enclosed, good job", exitscript=True)

with revit.Transaction("Delete unenclosed areas"):

    deleted = [] # to keep track of elements deleted
    # remove unenclosed areas
    for upid in unenclosed_ids:
        revit.doc.Delete(upid)
        deleted.append(upid)

    # print result
    print("Removed {} unenclosed areas".format(len(deleted)))
