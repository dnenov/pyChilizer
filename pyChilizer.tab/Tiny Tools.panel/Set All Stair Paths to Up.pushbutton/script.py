__title__ = "All Stair\nPath Up"
__doc__ = "Replace all Automatic Up / Down Stair Paths with Fixed Up Direction"


from pyrevit import revit, DB
from pyrevit.revit.db import query
from pyrevit import script

output = script.get_output()

auto_paths = DB.FilteredElementCollector(revit.doc) \
    .OfCategory(DB.BuiltInCategory.OST_StairsPaths) \
    .WherePasses(
        query.get_biparam_stringequals_filter(
            {DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM: "Automatic Up/Down Direction"}
        )).WhereElementIsNotElementType() \
   .ToElements()

up_path_id = DB.FilteredElementCollector(revit.doc) \
    .OfCategory(DB.BuiltInCategory.OST_StairsPaths) \
    .WherePasses(
        query.get_biparam_stringequals_filter(
            {DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM: "Fixed Up Direction"}
        )).WhereElementIsElementType() \
   .ToElementIds()

with revit.Transaction("Set all Stair Paths to Up"):
    for a in auto_paths:
        a.ChangeTypeId(up_path_id[0])



