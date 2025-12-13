from pyrevit import revit, DB, forms
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()

# todo: to add multi view option

all_plan_regions = DB.FilteredElementCollector(revit.doc) \
    .OfCategory(DB.BuiltInCategory.OST_PlanRegion) \
    .WhereElementIsNotElementType()

# filter by owner id instead of active view to get hidden elements
plan_region_ids = []
if all_plan_regions:
    for pr in all_plan_regions:
        if get_elementid_value(pr.OwnerViewId) == get_elementid_value(revit.active_view.Id):
            plan_region_ids.append(pr.Id)


forms.alert_ifnot(plan_region_ids, "No plan regions in view")
revit.get_selection().set_to(plan_region_ids)
