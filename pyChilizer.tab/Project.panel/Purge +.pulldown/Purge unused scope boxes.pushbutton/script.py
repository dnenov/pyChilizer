__title__ = "Purge Unused Scope Boxes"

from pyrevit import revit, DB, forms, script


def filter_sb_viewtypes(views):
    # returns only views of types compatible with scope box
    compatible_viewtypes = [
        DB.ViewType.FloorPlan,
        DB.ViewType.CeilingPlan,
        DB.ViewType.EngineeringPlan,
        DB.ViewType.AreaPlan,
        DB.ViewType.Section,
        DB.ViewType.Elevation,
        DB.ViewType.Detail,
        DB.ViewType.ThreeD
    ]
    filtered_views = [v for v in views if v.ViewType in compatible_viewtypes]
    return filtered_views


# collect all scope boxes
coll_scope = DB.FilteredElementCollector(revit.doc).OfCategory(DB.BuiltInCategory.OST_VolumeOfInterest).ToElementIds()
# collect all views
coll_views = DB.FilteredElementCollector(revit.doc).OfClass(DB.View).WhereElementIsNotElementType()
# filter views compatible with scope boxes
compatible_views = filter_sb_viewtypes(coll_views)

# get a list of used scope boxes
used_sb = []
for view in compatible_views:
    try:
        sb_id = view.get_Parameter(DB.BuiltInParameter.VIEWER_VOLUME_OF_INTEREST_CROP).AsElementId()
        if sb_id != DB.ElementId.InvalidElementId and sb_id not in used_sb:
            used_sb.append(sb_id)
    except:
        pass

with revit.Transaction("Purge Unused Scope Boxes"):
    # get ids of areas with location and zero area
    unused_ids = [sb for sb in coll_scope if sb not in set(used_sb)]

    deleted = []  # to keep track of elements deleted

    # remove unused scope boxes
    for usb_id in unused_ids:
        deleted.append(revit.doc.GetElement(usb_id).Name)
        revit.doc.Delete(usb_id)

    # print result
    if not deleted:
        print ("No Scope Boxes were deleted.")
    else:
        print("Purged unused Scope Boxes:")
        for d in deleted:
            print(d)