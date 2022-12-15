from pyrevit import revit, DB

view = revit.active_view
doc = revit.doc
collector = DB.FilteredElementCollector(doc, view.Id).WhereElementIsNotElementType().ToElementIds()

override = DB.OverrideGraphicSettings()
with revit.Transaction ("Reset Overrides"):
    for el_id in collector:
        view.SetElementOverrides(el_id, override)