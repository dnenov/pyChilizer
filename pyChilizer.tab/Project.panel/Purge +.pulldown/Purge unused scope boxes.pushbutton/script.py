__title__ = "Purge unused scope boxes"
__doc__ = "Removes scope boxes not used on any views or datum elements"
from pyrevit import revit, DB, forms, script
from pyrevit.framework import List

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

# exit if Scope Boxes found
forms.alert_ifnot(coll_scope, "No Scope Boxes in model.", exitscript=True)

# collect all views
coll_views = DB.FilteredElementCollector(revit.doc).OfClass(DB.View).WhereElementIsNotElementType()
# filter views compatible with scope boxes
compatible_views = filter_sb_viewtypes(coll_views)
# also collect levels and grids
cat_list = List[DB.BuiltInCategory]([DB.BuiltInCategory.OST_Levels, DB.BuiltInCategory.OST_Grids])
multi_cat_filter = DB.ElementMulticategoryFilter(cat_list)
coll_lvlgrids = DB.FilteredElementCollector(revit.doc).WherePasses(
    multi_cat_filter).WhereElementIsNotElementType()
# get a list of used scope boxes
used_sb = []
for view in compatible_views:
    try:
        sb_id = view.get_Parameter(DB.BuiltInParameter.VIEWER_VOLUME_OF_INTEREST_CROP).AsElementId()
        if sb_id != DB.ElementId.InvalidElementId and sb_id not in used_sb:
            used_sb.append(sb_id)
    except:
        pass

for datum in coll_lvlgrids:
    try:

        sb_id = datum.get_Parameter(DB.BuiltInParameter.DATUM_VOLUME_OF_INTEREST).AsElementId()
        if sb_id != DB.ElementId.InvalidElementId and sb_id not in used_sb:
            used_sb.append(sb_id)
    except:
        pass

# get unused scope boxes ids
unused_ids = [sb for sb in coll_scope if sb not in set(used_sb)]

forms.alert_ifnot(unused_ids, "All Scope Boxes are in use, well done!", exitscript=True)

message = 'There are {} unused Scope Boxes in the model. Are you sure you want to delete them?'.format(str(len(unused_ids)))

if forms.alert(message, ok=False, yes=True, no=True, exitscript=True):
    with revit.Transaction("Delete unused scope boxes"):

        deleted = []  # to keep track of elements deleted

        # remove unused scope boxes
        for usb_id in unused_ids:
            deleted.append(revit.doc.GetElement(usb_id).Name)
            revit.doc.Delete(usb_id)

        # print result
        if not deleted:
            print ("No Scope Boxes were deleted.")
        else:
            print("SCOPE BOXES DELETED:")
            for d in deleted:
                print("{}".format(d))