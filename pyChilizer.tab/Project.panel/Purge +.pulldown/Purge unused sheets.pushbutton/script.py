__title__ = "Purge unused sheets"
__doc__ = "Delete all the Sheets without Viewports or schedules on them."

from pyrevit import forms
from pyrevit import revit, DB
from pyrevit.framework import List
from pyrevit.forms import SheetOption, SelectFromList, TemplateListItem

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

FEC = DB.FilteredElementCollector
BIP = DB.BuiltInParameter


def get_sheet_nr(sheet_element):
    return sheet_element.get_Parameter(BIP.SHEET_NUMBER).AsValueString()


# custom ViewOption wrapper to display Sheet Number + Name
class SheetViewOption(TemplateListItem):
    def __init__(self, view_element):
        super(SheetViewOption, self).__init__(view_element)

    @property
    def name(self):
        """Sheet Number + name"""
        return '{} - {}'.format(get_sheet_nr(self.item), revit.query.get_name(self.item))


# custom form to select from a specific list of sheets instead of all sheets in the project
def select_sheets_preserve(title='Select Sheets to preserve',
                           button_name='Select',
                           width=600,
                           multiple=True,
                           sheets_to_keep=None
                           ):
    selected_sheets = SelectFromList.show(
        sorted([SheetViewOption(x) for x in sheets_to_keep],
               key=lambda x: x.name),
        title=title,
        group_selector_title='Sheet Sets:',
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True
    )

    return selected_sheets


# get the sheets with no viewports - this does not pick up sheets with schedules
sheets_with_no_views = [i for i in FEC(doc).OfClass(DB.ViewSheet).WhereElementIsNotElementType() if
                        len(i.GetAllPlacedViews()) == 0]

# get the schedules and sheets that they are placed on
schedules = FEC(doc).OfClass(DB.ScheduleSheetInstance).ToElements()
sheets_with_schedules = set()
for sch in schedules:
    if sch.IsTitleblockRevisionSchedule: # Skip revision schedules
        continue
    owner_id = sch.OwnerViewId
    if owner_id != DB.ElementId.InvalidElementId:
        sheet = doc.GetElement(owner_id)
        if isinstance(sheet, DB.ViewSheet):
            sheets_with_schedules.add(sheet.Id)  # use Id to be able to compare lists

sheets_with_no_views = [i for i in FEC(doc).OfClass(DB.ViewSheet).WhereElementIsNotElementType() if
                        len(i.GetAllPlacedViews()) == 0]

# subtract sheets with schedules from the list of sheets with no viewports
unused_sheets = [i for i in sheets_with_no_views if i.Id not in sheets_with_schedules]

if len(unused_sheets) == 0:
    forms.alert("No empty Sheets, well done!")
else:
    message = 'There are {} empty Sheets in the current model. Do you choose to proceed?'.format(
        str(len(unused_sheets)))
    if forms.alert(message, sub_msg="You can select the sheets to keep", ok=False, yes=True, no=True, exitscript=True):
        excluded_sheets = select_sheets_preserve(sheets_to_keep=unused_sheets)
        sheets_to_purge = List[DB.ElementId]([sh.Id for sh in unused_sheets if sh not in excluded_sheets])
        if not sheets_to_purge:
            forms.alert("No Sheets deleted.", exitscript=True)
        with revit.Transaction(__title__):
            try:
                s_names = [doc.GetElement(s).Title for s in sheets_to_purge]  # Get sheet names
                doc.Delete(sheets_to_purge)  # Delete the sheets
                # print result
                print("SHEETS DELETED:\n")
                for s in s_names:
                    print("{}".format(s))
            except:
                forms.alert("Could not execute the script (make sure there are no active empty Sheets).")
