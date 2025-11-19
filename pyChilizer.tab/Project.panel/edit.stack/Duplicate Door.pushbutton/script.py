"""Prep door placement based on a selected door."""

__title__ = 'Duplicate element'
__doc__ = 'Pick an element, duplicate its type.'

from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from pyrevit import revit, DB, UI, forms, script

doc = revit.doc
uidoc = revit.uidoc
logger = script.get_logger()


# BASICS

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

    # Try standard type name parameter
    param = symbol.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
    if param:
        try:
            name_val = param.AsString()
            if name_val and name_val.lower() != "none":
                return name_val
        except Exception:
            pass

    # Fallback to Name property
    try:
        name_val = symbol.Name
        if name_val and name_val.lower() != "none":
            return name_val
    except AttributeError:
        pass

    # Final fallback
    return "Unnamed Type"


def _get_family_name(element_type):
    """Get a readable family name for an ElementType, if possible."""
    if not element_type:
        return "Family"

    # Loadable families (FamilySymbol etc.)
    try:
        if hasattr(element_type, "Family") and element_type.Family:
            fam_name = element_type.Family.Name
            if fam_name:
                return fam_name
    except Exception:
        pass

    # Try a built-in parameter for family name
    try:
        fam_param = element_type.get_Parameter(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM)
        if fam_param:
            fam_name = fam_param.AsString()
            if fam_name:
                return fam_name
    except Exception:
        pass

    # Fallback: try category name
    try:
        if element_type.Category and element_type.Category.Name:
            return element_type.Category.Name
    except Exception:
        pass

    return "Unknown Family"

def _duplicate_type(source_type):
    """Duplicate the type of the selected element."""
    type_name = _get_symbol_name(source_type)
    default_name = "{} Copy".format(type_name)

    # Ask user for the new type name (can accept the default)
    new_name = forms.ask_for_string(
        default=default_name,
        prompt="Provide a name for the new type (leave blank to use the default)."
    )

    if not new_name:
        new_name = default_name

    # Duplicate inside a transaction
    with DB.Transaction(doc, "Duplicate Type") as t:
        t.Start()
        duplicated = source_type.Duplicate(new_name)

        # Some APIs return ElementId, some return the element itself
        if isinstance(duplicated, DB.ElementId):
            new_type = doc.GetElement(duplicated)
        else:
            new_type = duplicated

        t.Commit()

    logger.info("Duplicated type '{}' -> '{}'".format(type_name, _get_symbol_name(new_type)))
    return new_type



# SELECTION HELPERS

class TypeSelectionFilter(ISelectionFilter):
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
        with forms.WarningBar(title="Select an element to inspect"):
            ref = uidoc.Selection.PickObject(
                ObjectType.Element,
                TypeSelectionFilter(),
                "Select an element to inspect its family and type"
            )
        elem = doc.GetElement(ref.ElementId)
        if _has_type(elem):
            return elem
    except Exception as e:
        logger.debug("Selection cancelled or failed: {}".format(e))
        return None

    return None

#Inspecting 

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

family_name = _get_family_name(source_type)
type_name = _get_symbol_name(source_type)

forms.alert(
    "You selected:\nFamily: '{}'\nType:   '{}'".format(
        family_name,
        type_name
    ),
    ok=True
)

#Duplicate the type
try:
    new_type = _duplicate_type(source_type)
except Exception as dup_err:
    logger.error("Failed to duplicate type: {}".format(dup_err))
    forms.alert(
        "Could not duplicate the selected element type.\n"
        "Details: {}".format(dup_err),
        ok=True,
        exitscript=True
    )
    new_type = None

if not new_type:
    forms.alert("Could not prepare new type.", ok=True, exitscript=True)

#change the selected element to use the new duplicated type
try:
    _change_element_type(element, new_type)
except Exception as err:
    logger.error("Could not change element type: {}".format(err))
    forms.alert(
        "Could not change the element to the new type.\n"
        "Details: {}".format(err),
        ok=True,
        exitscript=True
    )

