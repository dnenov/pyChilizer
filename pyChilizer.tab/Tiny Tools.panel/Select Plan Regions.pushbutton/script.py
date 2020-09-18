__title__ = "Select\nPlan Region"
__doc__ = "Select all plan region elements in current view"

from pyrevit import revit, DB

# note: to add multi view option

plan_regions = DB.FilteredElementCollector(revit.doc, revit.active_view.Id) \
    .OfCategory(DB.BuiltInCategory.OST_PlanRegion) \
    .WhereElementIsNotElementType() \
    .ToElementIds()

revit.get_selection().set_to(plan_regions)
