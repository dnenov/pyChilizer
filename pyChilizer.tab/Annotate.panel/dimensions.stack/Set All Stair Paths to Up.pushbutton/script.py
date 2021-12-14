from pyrevit import revit, DB, forms, script

output = script.get_output()


paths = DB.FilteredElementCollector(revit.doc) \
    .OfCategory(DB.BuiltInCategory.OST_StairsPaths) \
    .WhereElementIsNotElementType()

path_types = DB.FilteredElementCollector(revit.doc) \
    .OfCategory(DB.BuiltInCategory.OST_StairsPaths) \
    .WhereElementIsElementType()


auto_paths = [p for p in paths if revit.doc.GetElement(p.GetTypeId()).StairsPathDirection == DB.Architecture.StairsPathDirection.AutomaticUpDown]
up_path_id = [p.Id for p in path_types if p.StairsPathDirection == DB.Architecture.StairsPathDirection.AlwaysUp]

stairs = DB.FilteredElementCollector(revit.doc) \
    .OfCategory(DB.BuiltInCategory.OST_Stairs) \
    .WhereElementIsNotElementType()

counter = 0
with revit.Transaction("Set all Stair Paths to Up"):
    for a in auto_paths:
        a.ChangeTypeId(up_path_id[0])
        counter += 1
    for stair in stairs:
        if stair.get_Parameter(DB.BuiltInParameter.STAIRS_INST_ALWAYS_UP):
            stair.get_Parameter(DB.BuiltInParameter.STAIRS_INST_ALWAYS_UP).Set(1)

forms.alert("Changed Stair Path direction to UP for {} stairs".format(counter))