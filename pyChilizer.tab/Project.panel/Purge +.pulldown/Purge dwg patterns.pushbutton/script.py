__title__ = "Purge imported dwg line patterns"
__doc__ = "Delete all the pesky imported dwg line patterns from the Project."

from pyrevit import forms
from pyrevit import revit, DB
from pyrevit.framework import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl = DB.FilteredElementCollector(doc)

pat_imports = List[DB.ElementId]([i.Id for i in cl.OfClass(DB.LinePatternElement) if "IMPORT" in i.Name])

l_num = str(len(pat_imports))
message = 'There are {} imported line patterns in the model. Are you sure you want to delete them?'.format(l_num)

if len(pat_imports) == 0:
    forms.alert("No Imported Line Patterns, well done!")
else:
    if forms.alert(message, ok=False, yes=True, no=True, exitscript=True):
        with revit.Transaction("Delete imported patterns"):
            doc.Delete(pat_imports)
            forms.alert("{} line patterns deleted.".format(l_num), warn_icon=False)




