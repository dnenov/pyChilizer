from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit import Exceptions
import rpw


# selection filter for rooms
class RoomsFilter(ISelectionFilter):
    def AllowElement(self, elem):
        try:
            if elem.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_Rooms):
                return True
            else:
                return False
        except AttributeError:
            return False

    def AllowReference(self, reference, position):
        try:
            if isinstance(revit.doc.GetElement(reference), DB.Room):
                return True
            else:
                return False
        except AttributeError:
            return False


'''Select Rooms'''


def select_rooms_filter():
    # select elements while applying category filter
    try:
        with forms.WarningBar(title="Pick Rooms to transform"):
            selection = [revit.doc.GetElement(reference) for reference in rpw.revit.uidoc.Selection.PickObjects(
                ObjectType.Element, RoomsFilter())]
            return selection
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, warn_icon=False, exitscript=True)


def preselection_with_filter(cat_name):
    # use pre-selection of elements, but filter them by given category name
    pre_selection = []
    for id in rpw.revit.uidoc.Selection.GetElementIds():
        sel_el = revit.doc.GetElement(id)
        if sel_el.Category.Name == cat_name:
            pre_selection.append(sel_el)
    return pre_selection
