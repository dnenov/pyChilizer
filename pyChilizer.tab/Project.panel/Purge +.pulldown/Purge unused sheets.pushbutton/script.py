__title__ = "Purge unused sheets"
__doc__ = "Delete all the Sheets without Viewports on them."

from pyrevit import forms
from pyrevit import revit, DB
from pyrevit.framework import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl = DB.FilteredElementCollector(doc)

sheets = List[DB.ElementId]\
    ([i.Id for i in cl.OfClass(DB.ViewSheet).WhereElementIsNotElementType() if len(i.GetAllViewports()) == 0])

message = 'There are {} empty Sheets in the current model. Are you sure you want to delete them?'.format(str(len(sheets)))

if len(sheets) == 0:
    forms.alert("No empty Sheets, well done!")
else:
    if forms.alert(message, ok=False, yes=True, no=True, exitscript=True):
        with revit.Transaction("Delete imported patterns"):
            try:
                doc.Delete(sheets)
            except:
                forms.alert("Could not execute the script (make sure there are no active empty Sheets).")




