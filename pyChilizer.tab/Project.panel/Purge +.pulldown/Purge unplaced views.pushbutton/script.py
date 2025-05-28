__title__ = "Purge unplaced Views"
__doc__ = "Delete all Views which have not been placed onto Sheets."

import sys

from pyrevit import forms
from pyrevit import revit, DB
from pyrevit.framework import List
from pyrevit.forms import SheetOption, SelectFromList, TemplateListItem

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl = DB.FilteredElementCollector(doc)


# name wrapper for forms
class ViewOption(TemplateListItem):
    def __init__(self, view_element):
        super(ViewOption, self).__init__(view_element)

    @property
    def name(self):
        """View Name"""
        return '{}'.format(revit.query.get_name(doc.GetElement(self.item)))


# custom form to select from a specific list of sheets instead of all sheets in the project
def select_views_to_preserve(title='Select Sheets to preserve',
                             button_name='Select Views to Keep',
                             width=600,
                             multiple=True,
                             sheets_to_keep=None
                             ):
    selected_sheets = SelectFromList.show(
        sorted([ViewOption(x) for x in sheets_to_keep],
               key=lambda x: x.name),
        title=title,
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True
    )

    return selected_sheets


viewports = List[DB.ElementId] \
    ([i.ViewId for i in cl.OfCategory(DB.BuiltInCategory.OST_Viewports).WhereElementIsNotElementType()])

views = List[DB.ElementId] \
    ([i.Id for i in
      DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Views).WhereElementIsNotElementType() if
      not i.IsTemplate])

unplaced_views = List[DB.ElementId]([v for v in views if v not in viewports])

message = 'There are {} unplaced Views in the current model. Are you sure you want to delete them?'.format(
    str(len(unplaced_views)))

if len(unplaced_views) == 0:
    forms.alert("No unplaced Views, well done!")
else:
    if forms.alert(message, sub_msg="You can select the views to keep. If you select none, all views will be purged.", ok=False, yes=True, no=True, exitscript=True):
        excluded_views = select_views_to_preserve(sheets_to_keep=unplaced_views)
        views_to_purge = List[DB.ElementId]([v for v in unplaced_views if v not in excluded_views])
        with revit.Transaction("Delete unplaced Views"):
            try:
                purged_names = []  # Get sheet names
                try:
                    for view in views_to_purge:
                        name = doc.GetElement(view).Name
                        doc.Delete(view)  # Delete the sheets 
                        purged_names.append(name)
                except:
                    pass
                # print result
                print("VIEWS DELETED:\n")
                for s in purged_names:
                    print("{}".format(s))
            except:
                forms.alert("Could not execute the script.")
