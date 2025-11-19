"""Prep door placement based on a selected door."""

__title__ = 'Duplicate element'
__doc__ = 'Pick an element, duplicate its type.'

from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from pyrevit import revit, DB, UI, forms, script

doc = revit.doc
uidoc = revit.uidoc
logger = script.get_logger()





def _has_type(elem):
    """Return True if the element has a valid type id."""
    if not elem:
        return False
    try:
        type_id = elem.GetTypeId()
    except Exception:
        return False

    if not type_id:
        return False

    return type_id != DB.ElementId.InvalidElementId


def _get_symbol_name(symbol):
    """Get a readable name for an ElementType."""
    if not symbol:
        return "Type"

#class TypeSelectionFilter(ISelectionFilter):
    def AllowElement(self, elem):
        # Allow any element that has a type
        return _has_type(elem)

    def AllowReference(self, reference, point):
        return True


def _get_preselected_element():
    """Return the first preselected element that has a type."""
    selected_ids = uidoc.Selection.GetElementIds()
    if not selected_ids:
        return None

    for eid in selected_ids:
        elem = doc.GetElement(eid)
        if _has_type(elem):
            return elem

    return None


def get_element():
    """Get an element from preselection or by picking in the model."""
    preselected = _get_preselected_element()
    if preselected:
        if forms.alert(
            "Use the pre-selected element?",
            yes=True,
            no=True
        ):
            return preselected

    # Otherwise prompt for selection
    try:
        with forms.WarningBar(title="Select an element to duplicate its type"):
            ref = uidoc.Selection.PickObject(
                ObjectType.Element,
                TypeSelectionFilter(),
                "Select an element to duplicate its type"
            )
        elem = doc.GetElement(ref.ElementId)
        if _has_type(elem):
            return elem
    except Exception as e:
        logger.debug("Selection cancelled or failed: {}".format(e))
        return None

    return None

element = get_element()
if not element:
    forms.alert(
        "No valid element selected. Please select an element that has a type.",
        ok=True,
        exitscript=True
    )

type_id = element.GetTypeId()
source_type = doc.GetElement(type_id) if type_id else None

if not source_type:
    forms.alert("Selected element has no valid type.", ok=True, exitscript=True)

# Get readable type name
type_name = _get_symbol_name(source_type)

# Show element & type information
forms.alert(
    "You selected element ID {}.\nIts current type is:\n'{}'".format(
        str(element.Id),     # FIXED: no more .IntegerValue
        type_name
    ),
    ok=True
)