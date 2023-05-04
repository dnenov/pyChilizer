from pyrevit import revit, DB

view = revit.active_view
doc = revit.doc

with revit.Transaction ("Remove Filters"):
    for filter in view.GetFilters():
        view.RemoveFilter(filter)