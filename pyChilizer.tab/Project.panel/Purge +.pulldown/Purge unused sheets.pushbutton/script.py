__title__ = "Purge unused sheets"
__doc__ = "Delete all the Sheets without Viewports on them, skipping opened sheets."

from pyrevit import forms
from pyrevit import revit, DB
from pyrevit.framework import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl = DB.FilteredElementCollector(doc)

# Get all empty sheets
all_empty_sheets = [i for i in cl.OfClass(DB.ViewSheet).WhereElementIsNotElementType() if len(i.GetAllViewports()) == 0]

# Get currently opened views in the active document
open_views = []
try:
    for ui_view in uidoc.GetOpenUIViews():
        open_views.append(ui_view.ViewId)
except:
    pass

# Also check the active view
active_view_id = uidoc.ActiveView.Id

# Filter out sheets that are currently opened
sheets_to_delete = []
opened_sheets_skipped = []

for sheet in all_empty_sheets:
    is_in_open_views = sheet.Id in open_views
    is_active_view = sheet.Id == active_view_id
    is_opened = is_in_open_views or is_active_view
    
    if is_opened:
        opened_sheets_skipped.append(sheet.Title)
    else:
        sheets_to_delete.append(sheet.Id)

sheets = List[DB.ElementId](sheets_to_delete)

if len(sheets) == 0 and len(opened_sheets_skipped) == 0:
    forms.alert("No empty Sheets, well done!")
elif len(sheets) == 0 and len(opened_sheets_skipped) > 0:
    forms.alert("All empty sheets are currently opened and will be skipped.")
else:
    message = 'There are {} empty Sheets in the current model.'.format(str(len(all_empty_sheets)))
    if len(opened_sheets_skipped) > 0:
        message += '\n\n{} opened sheets will be skipped:'.format(len(opened_sheets_skipped))
        for sheet_name in opened_sheets_skipped[:5]:  # Show first 5
            message += '\n- {}'.format(sheet_name)
        if len(opened_sheets_skipped) > 5:
            message += '\n... and {} more'.format(len(opened_sheets_skipped) - 5)
        message += '\n\nAre you sure you want to delete the remaining {} sheets?'.format(len(sheets))
    else:
        message += ' Are you sure you want to delete them?'
    
    if forms.alert(message, ok=False, yes=True, no=True, exitscript=True):
        with revit.Transaction(__title__):
            try:
                s_names = [doc.GetElement(s).Title for s in sheets] # Get sheet names  
                doc.Delete(sheets)  # Delete the sheets 
                # print result
                print("SHEETS DELETED:\n")
                for s in s_names:
                    print("{}".format(s))
                
                if len(opened_sheets_skipped) > 0:
                    print("\nSHEETS SKIPPED (currently opened):\n")
                    for s in opened_sheets_skipped:
                        print("{}".format(s))
            except:
                forms.alert("Could not execute the script (make sure there are no active empty Sheets).")




