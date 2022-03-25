from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit import Exceptions
import rpw


class CatFilter(ISelectionFilter):
    def __init__(self, cat):
        self.cat = cat

    def AllowElement(self, elem):
        try:
            if elem.Category.Id.IntegerValue == int(self.cat):
                return True
            else:
                return False
        except AttributeError:
            return False

    def AllowReference(self, reference):
        try:
            if isinstance(revit.doc.GetElement(reference), self.cat):
                return True
            else:
                return False
        except AttributeError:
            return False


def select_with_cat_filter(cat, message):
    pre_selection = preselection_with_filter(cat)
    if pre_selection and forms.alert(
            "You have selected {} elements. Do you want to use them?".format(len(pre_selection))):
        selection = pre_selection
    else:
        # select elements while applying category filter
        try:
            with forms.WarningBar(title=message):
                selection = [revit.doc.GetElement(reference) for reference in rpw.revit.uidoc.Selection.PickObjects(
                    ObjectType.Element, CatFilter(cat=cat))]
        except Exceptions.OperationCanceledException:
            forms.alert("Cancelled", ok=True, warn_icon=False, exitscript=True)
    if not selection:
        forms.alert("You need to select at least one Room.", exitscript=True)
    return selection

def select_rooms_filter():
    # select elements while applying category filter
    try:
        with forms.WarningBar(title="Pick Rooms to transform"):
            selection = [revit.doc.GetElement(reference) for reference in rpw.revit.uidoc.Selection.PickObjects(
                ObjectType.Element, RoomsFilter())]
            return selection
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, warn_icon=False, exitscript=True)


def preselection_with_filter(cat):
    # use pre-selection of elements, but filter them by given category name
    pre_selection = []
    for id in rpw.revit.uidoc.Selection.GetElementIds():
        sel_el = revit.doc.GetElement(id)
        if sel_el.Category.Id.IntegerValue == int(cat):
            pre_selection.append(sel_el)
    return pre_selection


