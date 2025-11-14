"""Prep door placement based on a selected door."""

__title__ = 'Duplicate Door'
__doc__ = 'Pick a door, duplicate its type, open properties, and start placement.'

from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from pyrevit import revit, DB, UI, forms, script

doc = revit.doc
uidoc = revit.uidoc
logger = script.get_logger()


DOOR_CATEGORY_ID = DB.ElementId(DB.BuiltInCategory.OST_Doors)


def _is_door(elem):
    if not isinstance(elem, DB.FamilyInstance):
        return False
    cat = elem.Category
    if not cat:
        return False
    return cat.Id == DOOR_CATEGORY_ID


def _get_symbol_name(symbol):
    if not symbol:
        return "Door Type"
    param = symbol.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
    if param:
        try:
            name_val = param.AsString()
            if name_val:
                return name_val
        except Exception:
            pass
    try:
        return symbol.Name
    except AttributeError:
        return "Door Type"


class DoorSelectionFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return _is_door(elem)

    def AllowReference(self, reference, point):
        return True


def _get_preselected_door():
    selected_ids = uidoc.Selection.GetElementIds()
    if not selected_ids:
        return None
    for eid in selected_ids:
        elem = doc.GetElement(eid)
        if _is_door(elem):
            return elem
    return None


def _generate_unique_type_name(base_name, family):
    existing = set()
    for sid in family.GetFamilySymbolIds():
        sym = doc.GetElement(sid)
        if sym:
            existing.add(_get_symbol_name(sym))

    if base_name and base_name not in existing:
        return base_name

    counter = 1
    base = base_name or "New Door Type"
    while True:
        candidate = "{} ({})".format(base, counter)
        if candidate not in existing:
            return candidate
        counter += 1


def _duplicate_symbol(symbol):
    symbol_name = _get_symbol_name(symbol)
    family = symbol.Family
    default_name = _generate_unique_type_name("{} Copy".format(symbol_name), family)
    new_name = forms.ask_for_string(
        default=default_name,
        prompt="Provide a name for the new door type (leave blank to use default)."
    )
    if not new_name:
        new_name = default_name
    new_name = _generate_unique_type_name(new_name, family)

    with DB.Transaction(doc, "Duplicate Door Type") as t:
        t.Start()
        duplicated = symbol.Duplicate(new_name)
        if isinstance(duplicated, DB.ElementId):
            new_symbol = doc.GetElement(duplicated)
        else:
            new_symbol = duplicated
        if not new_symbol.IsActive:
            new_symbol.Activate()
            doc.Regenerate()
        t.Commit()

    logger.info("Duplicated door type '{}' -> '{}'".format(symbol_name, new_name))
    return new_symbol


def _change_door_type(door, new_symbol):
    """change the door instance to use the new symbol."""
    with DB.Transaction(doc, "Change Door symbol") as t:
        t.Start()
        door.ChangeTypeId(new_symbol.Id)
        t.Commit()
    logger.info("Changed door '{}' to use type '{}'".format(_get_symbol_name(door), _get_symbol_name(new_symbol)))


# Get door from selection or prompt user
def get_door():
    preselected = _get_preselected_door()
    if preselected:
        if forms.alert(
            "Use the pre-selected door?",
            yes=True,
            no=True
        ):
            return preselected

    # Otherwise prompt for selection
    try:
        with forms.WarningBar(title="Select a door to duplicate and change"):
            ref = uidoc.Selection.PickObject(
                ObjectType.Element,
                DoorSelectionFilter(),
                "Select a door to duplicate and change"
            )
        door = doc.GetElement(ref.ElementId)
        if _is_door(door):
            return door
    except Exception as e:
        logger.debug("Selection cancelled or failed: {}".format(e))
        return None
    return None


# Main flow
door = get_door()
if not door:
    forms.alert("No door selected. Please select a door to duplicate.", ok=True, exitscript=True)

type_id = door.GetTypeId()
source_symbol = doc.GetElement(type_id) if type_id else None
if not source_symbol:
    forms.alert("Selected door has no type.", ok=True, exitscript=True)

try:
    target_symbol = _duplicate_symbol(source_symbol)
except Exception as dup_err:
    logger.error("Failed to duplicate door type: {}".format(dup_err))
    forms.alert(
        "Could not duplicate the selected door type.\n"
        "Details: {}".format(dup_err),
        ok=True,
        exitscript=True
    )
    target_symbol = None

if not target_symbol:
    forms.alert("Could not prepare door type.", ok=True, exitscript=True)

# Change the existing odoor to the new type
try:
    _change_door_type(door, target_symbol)
except Exception as err:
    logger.error("Could not change door type: {}".format(err))
    forms.alert("Could not change the door to the new type.\n"
                "Details: {}".format(err),
                ok=True,
                exitscript=True
    )

# Open the standard Revit Type Properties dialog for the active type
type_cmd = UI.RevitCommandId.LookupPostableCommandId(UI.PostableCommand.TypeProperties)
if type_cmd:
    try:
        revit.ui.PostCommand(type_cmd)
    except Exception as err:
        logger.debug("Type Properties command failed: {}".format(err))

# Toggle the Properties palette (same as pressing PP)
toggle_cmd = UI.RevitCommandId.LookupPostableCommandId(UI.PostableCommand.TogglePropertiesPalette)
if toggle_cmd:
    try:
        revit.ui.PostCommand(toggle_cmd)
    except Exception as err:
        logger.debug("Toggle Properties command failed: {}".format(err))

target_symbol_name = _get_symbol_name(target_symbol)

msg = "Door changed to duplicated type '{}'.".format(target_symbol_name)
msg += "\nType Properties opened. Properties palette toggled (press PP if it closed instead)."

try:
    forms.toast(msg, title="Duplicate Door", appid="pyChilizer")
except Exception:
    logger.info(msg)

