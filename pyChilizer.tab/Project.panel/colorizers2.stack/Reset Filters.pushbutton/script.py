from pyrevit import revit, DB

view = revit.active_view
doc = revit.doc
# collector = DB.FilteredElementCollector(doc, view.Id).WhereElementIsNotElementType().ToElementIds()
# override = DB.OverrideGraphicSettings()

with revit.Transaction ("Reset Overrides"):
    for filter in view.GetFilters():
        view.RemoveFilter(filter)