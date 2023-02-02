__title__ = "Purge unplaced Views"
__doc__ = "Delete all Views which have not been placed onto Sheets."

from pyrevit import forms
from pyrevit import revit, DB
from pyrevit.framework import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl = DB.FilteredElementCollector(doc)

viewports = List[DB.ElementId]\
    ([i.ViewId for i in cl.OfCategory(DB.BuiltInCategory.OST_Viewports).WhereElementIsNotElementType()])

views = List[DB.ElementId]\
    ([i.Id for i in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Views).WhereElementIsNotElementType()])

unplaced_views = List[DB.ElementId]([v for v in views if v not in viewports])

message = 'There are {} unplaced Views in the current model. Are you sure you want to delete them?'.format(str(len(unplaced_views)))

if len(unplaced_views) == 0:
    forms.alert("No unpolaced Views, well done!")
else:
    if forms.alert(message, ok=False, yes=True, no=True, exitscript=True):
        with revit.Transaction("Delete unplaced Views"):
            try:
                unplaced_names = [] # Get sheet names  
                try:
                    for view in unplaced_views:
                        name = doc.GetElement(view).Name
                        doc.Delete(view)  # Delete the sheets 
                        unplaced_names.append(name)
                except:
                    pass
                # print result
                print("VIEWS DELETED:\n")
                for s in unplaced_names:
                    print("{}".format(s))
            except:
                forms.alert("Could not execute the script.")




