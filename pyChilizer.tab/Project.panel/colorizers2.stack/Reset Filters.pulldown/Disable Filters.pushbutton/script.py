from pyrevit import revit, DB

view = revit.active_view
doc = revit.doc

with revit.Transaction ("Disable Filters"):
    for filter in view.GetFilters():
        view.SetIsFilterEnabled(filter, False)
