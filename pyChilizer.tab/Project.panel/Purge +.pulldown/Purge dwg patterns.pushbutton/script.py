__title__ = "Purge dwg"
__doc__ =

from pyrevit import forms
from pyrevit import revit, DB

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document


imports = DB.FilteredElementCollector(doc).OfClass(DB.ImportedInstance).ToList()

print(imports)