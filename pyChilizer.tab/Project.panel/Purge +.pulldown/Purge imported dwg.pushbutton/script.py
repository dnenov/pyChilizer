__title__ = "Purge imported dwg"
__doc__ = "Delete all the imported dwg from the Project. All of them."

from pyrevit import forms
from pyrevit import revit, DB
from pyrevit.framework import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl = DB.FilteredElementCollector(doc)

cad_imports = List[DB.ElementId]([i.Id for i in cl.OfClass(DB.ImportInstance) if not i.IsLinked])

message = 'There are {} cad imports in the model. Are you sure you want to delete them?'.format(str(len(cad_imports)))

if len(cad_imports) == 0:
    forms.alert("No Imports, well done!")
else:
    if forms.alert(message, ok=False, yes=True, no=True, exitscript=True):
        with revit.Transaction("Remove dwg imports"):
            for id in cad_imports:
                try:
                    doc.Delete(cad_imports)
                except:
                    continue




