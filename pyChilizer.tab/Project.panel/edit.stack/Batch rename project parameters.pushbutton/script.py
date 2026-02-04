
__title__ = 'Batch rename shared project parameters'
__doc__ = 'Creates new sharedproject parameters by replacing one text value in the parameter name with another and copies values from the original parameters.'

from pyrevit import revit, DB, forms
import os
import sys

doc = revit.doc
app = doc.Application

DEFAULT_OLD = ""
DEFAULT_NEW = ""
DEFAULT_GROUP = ""


def temp_sp_path():
    # creates a temp file path for shared parameters
    temp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
    return os.path.join(temp_dir, "pyrevit_auto_rename_shared_params.txt")


def ensure_sp_file(path):
    # makes sure the file exists, creates it if not
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("# Created by pyRevit AUTO_RENAME\n")
    return path


def open_sp_file():
    # opens the shared parameter file, or creates temp one
    sp_path = app.SharedParametersFilename
    if not sp_path or not os.path.exists(sp_path):
        sp_path = ensure_sp_file(temp_sp_path())
        app.SharedParametersFilename = sp_path
    return app.OpenSharedParameterFile(), sp_path


def ensure_group(def_file, name):
    # gets existing group or makes a new one
    grp = def_file.Groups.get_Item(name)
    return grp if grp else def_file.Groups.Create(name)


def get_category_set(binding):
    # pulls out the categories from the binding
    cat_set = app.Create.NewCategorySet()
    try:
        for cat in binding.Categories:
            cat_set.Insert(cat)
    except:
        pass
    return cat_set


def is_instance_binding(binding):
    return isinstance(binding, DB.InstanceBinding)


def is_shared_definition(definition):
    # checks if parameter is shared
    try:
        return definition.IsShared
    except:
        return True



def find_definition_by_name(doc, name):
    # looks through all parameters to find one by name
    it = doc.ParameterBindings.ForwardIterator()
    it.Reset()
    while it.MoveNext():
        d = it.Key
        if d and d.Name == name:
            return d
    return None


def get_all_elements_with_param(param_name, is_type_param=False):
    # finds all elements that have this parameter
    all_elements = []

    if is_type_param:
        collector = DB.FilteredElementCollector(doc).WhereElementIsElementType()
    else:
        collector = DB.FilteredElementCollector(doc).WhereElementIsNotElementType()

    for elem in collector:
        param = elem.LookupParameter(param_name)
        if param and not param.IsReadOnly:
            all_elements.append(elem)

    return all_elements


def copy_parameter_value(elem, old_param_name, new_param_name):
    # copies value from old param to new param
    old_param = elem.LookupParameter(old_param_name)
    new_param = elem.LookupParameter(new_param_name)

    if not old_param or not new_param:
        return False

    if old_param.IsReadOnly or new_param.IsReadOnly:
        return False

    try:
        if not old_param.HasValue:
            return False

        storage_type = old_param.StorageType

        # different types need different methods
        if storage_type == DB.StorageType.String:
            new_param.Set(old_param.AsString() or "")
        elif storage_type == DB.StorageType.Integer:
            new_param.Set(old_param.AsInteger())
        elif storage_type == DB.StorageType.Double:
            new_param.Set(old_param.AsDouble())
        elif storage_type == DB.StorageType.ElementId:
            new_param.Set(old_param.AsElementId())

        return True
    except:
        return False


#  get user input
old_token = forms.ask_for_string(
    default=DEFAULT_OLD,
    prompt="Old token to replace",
    title="AUTO_RENAME"
)
if not old_token:
    sys.exit()

new_token = forms.ask_for_string(
    default=DEFAULT_NEW,
    prompt="New token (replacement)",
    title="AUTO_RENAME"
)
if not new_token:
    sys.exit()

old_token = old_token.strip()
new_token = new_token.strip()

if not old_token or not new_token:
    forms.alert("Both tokens required", exitscript=True)

if old_token == new_token:
    forms.alert("Tokens must be different", exitscript=True)

group_name = forms.ask_for_string(
    default=DEFAULT_GROUP,
    prompt="Shared parameter group name for new parameters",
    title="AUTO_RENAME"
)
if not group_name:
    sys.exit()

group_name = group_name.strip()
if not group_name:
    forms.alert("Group name is required", exitscript=True)


# collect all parameters
bindings_map = doc.ParameterBindings
iterator = bindings_map.ForwardIterator()
iterator.Reset()

candidates = []
skipped_not_shared = 0
checked_api = False

# loop through parameters
while iterator.MoveNext():
    definition = iterator.Key
    binding = iterator.Current
    if not definition:
        continue

    name = definition.Name or ""
    if old_token not in name:
        continue


    # skip if not shared
    if not is_shared_definition(definition):
        skipped_not_shared += 1
        continue

    cat_set = get_category_set(binding)
    if cat_set.Size == 0:
        continue

    new_name = name.replace(old_token, new_token)
    is_type_param = not is_instance_binding(binding)

    # get parameter info
    group_type_id = definition.GetGroupTypeId()
    dtype = definition.GetDataType()

    try:
        varies_across_groups = definition.VariesAcrossGroups
    except:
        varies_across_groups = False

    # save this parameter as a candidate
    candidates.append({
        "old_def": definition,
        "old_name": name,
        "new_name": new_name,
        "cat_set": cat_set,
        "is_type_param": is_type_param,
        "group_type_id": group_type_id,
        "varies_across_groups": varies_across_groups,
        "dtype": dtype
    })

if not candidates:
    forms.alert("No matching shared project parameters found", exitscript=True)


#  Show preview to user
report_lines = [
    "Found {} parameters containing '{}'".format(len(candidates), old_token),
    "Skipped not-shared: {}".format(skipped_not_shared),
    "",
    "Preview of changes:",
    ""
]

for c in candidates:
    bind_type = "Type" if c["is_type_param"] else "Instance"
    report_lines.append("  {} -> {} [{}]".format(c["old_name"], c["new_name"], bind_type))

report_lines.extend([
    "",
    "This will:",
    "  1. Create new shared parameter definitions",
    "  2. Bind them to the project",
    "  3. Copy all values from old to new parameters",
    "  4. Delete old parameters",
    "",
    "Make sure you have a backup of your project"
])

proceed = forms.alert(
    "\n".join(report_lines),
    title="AUTO_RENAME - Confirm Changes",
    ok=True,
    cancel=True
)
if not proceed:
    sys.exit()


# open shared params file
def_file, sp_path = open_sp_file()
if def_file is None:
    forms.alert("Could not open shared parameter file", exitscript=True)

grp = ensure_group(def_file, group_name)


# keep track of results
stats = {
    "found": len(candidates),
    "skipped_not_shared": skipped_not_shared,
    "created_defs": 0,
    "existed_defs": 0,
    "failed_create_defs": 0,
    "bound": 0,
    "failed_bind": 0,
    "varies_set_ok": 0,
    "varies_set_failed": 0,
    "deleted": 0,
    "failed_delete": 0
}

created_defs = {}


# create new definitions in shared params file
for c in candidates:
    new_name = c["new_name"]

    # check if it already exists
    try:
        existing = grp.Definitions.get_Item(new_name)
        if existing:
            created_defs[new_name] = existing
            stats["existed_defs"] += 1
            continue
    except:
        pass

    # create the new definition
    try:
        opts = DB.ExternalDefinitionCreationOptions(new_name, c["dtype"])
        opts.Visible = True
        new_def = grp.Definitions.Create(opts)
        created_defs[new_name] = new_def
        stats["created_defs"] += 1
    except:
        created_defs[new_name] = None
        stats["failed_create_defs"] += 1
        print("Failed to create: {}".format(new_name))


# bind new parameters to project
with revit.Transaction("Bind new parameters"):
    for c in candidates:
        new_name = c["new_name"]
        new_def = created_defs.get(new_name)

        if not new_def:
            stats["failed_bind"] += 1
            continue

        try:
            # create the binding
            if c["is_type_param"]:
                new_binding = app.Create.NewTypeBinding(c["cat_set"])
            else:
                new_binding = app.Create.NewInstanceBinding(c["cat_set"])

            # insert or reinsert
            if bindings_map.Contains(new_def):
                bindings_map.ReInsert(new_def, new_binding, c["group_type_id"])
            else:
                bindings_map.Insert(new_def, new_binding, c["group_type_id"])

            stats["bound"] += 1

            # set the varies by group property
            try:
                new_proj_def = find_definition_by_name(doc, new_name)
                if new_proj_def:
                    new_proj_def.SetAllowVaryBetweenGroups(doc, c["varies_across_groups"])
                    stats["varies_set_ok"] += 1
                else:
                    stats["varies_set_failed"] += 1
            except:
                stats["varies_set_failed"] += 1

        except:
            stats["failed_bind"] += 1
            print("Failed to bind: {}".format(new_name))


# copy values from old params to new params
with revit.Transaction("Copy values to new parameter"):
    for c in candidates:
        old_name = c["old_name"]
        new_name = c["new_name"]
        is_type_param = c["is_type_param"]

        elements = get_all_elements_with_param(old_name, is_type_param)

        # copy for each element
        for elem in elements:
            old_p = elem.LookupParameter(old_name)
            new_p = elem.LookupParameter(new_name)

            if not old_p or not new_p:
                continue
            if old_p.IsReadOnly or new_p.IsReadOnly:
                continue
            if not old_p.HasValue:
                continue

            copy_parameter_value(elem, old_name, new_name)


# delete old parameters
with revit.Transaction("Delete old parameters"):
    for c in candidates:
        try:
            bindings_map.Remove(c["old_def"])
            stats["deleted"] += 1
        except:
            stats["failed_delete"] += 1
            print("Failed to delete: {}".format(c["old_name"]))

# show results
final_report = [
    "AUTO_RENAME COMPLETE",
    "",
    "SHARED PARAMETER FILE:",
    "  {}".format(sp_path),
    "  Group: {}".format(group_name),
    "",
    "FOUND:",
    "  Candidates: {}".format(stats["found"]),
    "  Skipped not-shared: {}".format(stats["skipped_not_shared"]),
    "",
    "NEW DEFINITIONS:",
    "  Created: {}".format(stats["created_defs"]),
    "  Already existed: {}".format(stats["existed_defs"]),
    "  Failed to create: {}".format(stats["failed_create_defs"]),
    "",
    "BINDING:",
    "  Successfully bound: {}".format(stats["bound"]),
    "  Failed to bind: {}".format(stats["failed_bind"]),
    "",
    "VARY BY GROUP INSTANCE:",
    "  Set OK: {}".format(stats["varies_set_ok"]),
    "  Set failed: {}".format(stats["varies_set_failed"]),
    "",
    "CLEANUP:",
    "  Old parameters deleted: {}".format(stats["deleted"]),
    "  Failed to delete: {}".format(stats["failed_delete"]),
    "",
    "Total parameters renamed: {}".format(stats["bound"])
]

if (
    stats["failed_create_defs"] > 0 or
    stats["failed_bind"] > 0 or
    stats["failed_delete"] > 0 or
    stats["varies_set_failed"] > 0
):
    final_report.append("")
    final_report.append("Some operations failed. Check printed output and verify project parameters.")

forms.alert("\n".join(final_report), title="AUTO_RENAME - Complete")