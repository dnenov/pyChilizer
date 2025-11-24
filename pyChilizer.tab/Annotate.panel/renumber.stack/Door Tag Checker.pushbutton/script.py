__title__ = 'Door Tag Checker'
__doc__ = 'Analyse if doors are tagged in selected views and check for inconsistencies.'


from pyrevit import revit, DB, script, forms

doc = revit.doc
logger = script.get_logger()
output = script.get_output()
config = script.get_config()   # used to remember last-selected views


def get_all_potential_views():
    """
    Collect all non-template views where tags could appear.
    (Excludes schedules, legends, browsers, etc.)
    """
    excluded_types = {
        DB.ViewType.ProjectBrowser,
        DB.ViewType.SystemBrowser,
        DB.ViewType.Schedule,
        DB.ViewType.Report,
        DB.ViewType.Internal,
        DB.ViewType.Undefined,
        DB.ViewType.Legend
    }

    views = []
    allviews = DB.FilteredElementCollector(doc) \
                 .OfClass(DB.View) \
                 .ToElements()

    for v in allviews:
        if v.IsTemplate:
            continue
        try:
            if v.ViewType in excluded_types:
                continue
        except:
            # If something weird happens, just ignore and keep going
            pass
        views.append(v)

    return views


class ViewOption(forms.TemplateListItem):
    """Wrapper for selecting views from a grouped list."""

    def __init__(self, view):
        super(ViewOption, self).__init__(view)

    @property
    def name(self):
        # What the user sees in the list, e.g.:
        # "Level 01 [FloorPlan]"
        try:
            vt_name = str(self.item.ViewType)
        except:
            vt_name = "View"
        return "{} [{}]".format(self.item.Name, vt_name)


def categorize_selected_views(selected_views):
    """
    Split selected views into:
    - plan_like_views
    - elev_like_views
    based on ViewType.
    """

    plan_types = {
        DB.ViewType.FloorPlan,
        DB.ViewType.CeilingPlan,
        DB.ViewType.EngineeringPlan,
        DB.ViewType.AreaPlan
    }

    elev_types = {
        DB.ViewType.Elevation,
        DB.ViewType.Section,
        DB.ViewType.Detail,
        DB.ViewType.DraftingView,
        DB.ViewType.ThreeD
    }

    plan_views = []
    elev_views = []

    for v in selected_views:
        try:
            vt = v.ViewType
        except:
            continue

        if vt in plan_types:
            plan_views.append(v)
        elif vt in elev_types:
            elev_views.append(v)

    return plan_views, elev_views


def select_views():
    """
    Show a grouped menu (by ViewType) with all potential views.
    User can tick any combination.
    Remembers last selection and pre-selects those views.
    """

    all_potential_views = get_all_potential_views()

    if not all_potential_views:
        forms.alert("No suitable views found in this model.",
                    title="Door Tag Checker")
        return [], []

    # Load last selection (stored as list of IntegerValue IDs)
    try:
        last_ids = set(getattr(config, "last_view_ids", []) or [])
    except:
        last_ids = set()

    grouped = {}
    all_options = []

    # Build grouped dict and keep a flat list of all options
    for v in all_potential_views:
        opt = ViewOption(v)
        all_options.append(opt)

        try:
            group_name = str(v.ViewType)
        except:
            group_name = "Other"

        if group_name not in grouped:
            grouped[group_name] = []

        grouped[group_name].append(opt)

    # Build default (pre-selected) options from last_ids
    default_opts = []
    if last_ids:
        for opt in all_options:
            try:
                if opt.item.Id.IntegerValue in last_ids:
                    default_opts.append(opt)
            except:
                continue

    # Show UI
    selected_views_raw = forms.SelectFromList.show(
        grouped,
        title="Select Views to Check Door Tags",
        button_name="Check Doors",
        multiselect=True,
        default=default_opts if default_opts else None
    )

    if not selected_views_raw:
        forms.alert("No views selected.", title="Door Tag Checker")
        return [], []

    # Normalise returned objects into DB.View
    selected_views = []
    for x in selected_views_raw:
        if isinstance(x, DB.View):
            selected_views.append(x)
        elif hasattr(x, 'item') and isinstance(x.item, DB.View):
            selected_views.append(x.item)

    if not selected_views:
        forms.alert("No valid views selected.", title="Door Tag Checker")
        return [], []

    # Persist current selection for next run
    try:
        config.last_view_ids = [v.Id.IntegerValue for v in selected_views]
        script.save_config()
    except:
        pass

    # Categorise into plan-like and elev/section-like
    plan_views, elev_views = categorize_selected_views(selected_views)

    if not plan_views and not elev_views:
        forms.alert("Selected views are not plan/elevation types.", title="Door Tag Checker")
        return [], []

    return plan_views, elev_views


def get_all_doors():
    """
    Collect all door instances from the model.
    """
    doors = DB.FilteredElementCollector(doc) \
              .OfCategory(DB.BuiltInCategory.OST_Doors) \
              .WhereElementIsNotElementType() \
              .ToElements()
    return list(doors)


def get_tagged_door_ids_by_view(views, door_ids):
    """
    For each view in 'views', return a mapping:
        { view : set(door_ids tagged in that view) }
    """
    tagged_by_view = {}

    for view in views:
        view_tagged_ids = set()
        try:
            tags = DB.FilteredElementCollector(doc, view.Id) \
                     .OfCategory(DB.BuiltInCategory.OST_DoorTags) \
                     .ToElements()

            for tag in tags:
                tagged_id = None

                try:
                    # Different Revit versions expose different properties / types
                    if hasattr(tag, 'TaggedElementId'):
                        teid = tag.TaggedElementId
                        # In newer Revit, this may be a LinkElementId
                        if hasattr(teid, 'ElementId'):
                            tagged_id = teid.ElementId
                        else:
                            tagged_id = teid
                    elif hasattr(tag, 'TaggedLocalElementId'):
                        tagged_id = tag.TaggedLocalElementId
                    else:
                        # Fallback: try references
                        refs = tag.GetTaggedReferences()
                        if refs and len(refs) > 0:
                            tagged_id = refs[0].ElementId
                except:
                    tagged_id = None

                # Only keep door IDs we care about
                if tagged_id and tagged_id in door_ids:
                    view_tagged_ids.add(tagged_id)
        except:
            # if the view can't be processed, just skip it
            pass

        tagged_by_view[view] = view_tagged_ids

    return tagged_by_view


def safe_name(element, default=""):
    """
    Safely get the name of an element, returning default if unavailable.
    """
    if not element:
        return default
    try:
        name = element.Name
        return name if name else default
    except:
        return default


def get_mark_value(door):
    """
    Get the Mark parameter value from a door element.
    """
    try:
        mark_param = door.get_Parameter(DB.BuiltInParameter.DOOR_NUMBER)
        if mark_param and mark_param.HasValue:
            return mark_param.AsString()
    except:
        pass
    return ""


def run():
    # Main entry point when I click the pychilizer button.

    doors = get_all_doors()
    if not doors:
        output.print_md("No doors found in the model.")
        return

    # store all door ids in a set so I can test quickly.
    door_ids = set(d.Id for d in doors)

    # Get selected views from user
    plan_views, elev_views = select_views()
    if not plan_views and not elev_views:
        return  # User cancelled or no valid views

    # Combine all selected views into one ordered list
    selected_views = list(plan_views) + list(elev_views)

    # For each view, get which doors are tagged there
    tagged_by_view = get_tagged_door_ids_by_view(selected_views, door_ids)

    all_rows = []
    inconsistent_rows = []

    for door in doors:
        did = door.Id
        id_link = output.linkify(did)

        type_elem = doc.GetElement(door.GetTypeId())
        type_name = safe_name(type_elem, "No Type")

        mark_val = get_mark_value(door)

        # For each selected view: is this door tagged in that view?
        per_view_yesno = []
        yes_count = 0
        no_count = 0

        for v in selected_views:
            tagged_ids_for_view = tagged_by_view.get(v, set())
            if did in tagged_ids_for_view:
                per_view_yesno.append("Yes")
                yes_count += 1
            else:
                per_view_yesno.append("No")
                no_count += 1

        # Status: OK if door is either tagged in ALL or NONE of the selected views
        # Inconsistent if it's a mix of Yes and No.
        if yes_count == 0 or no_count == 0:
            status = "OK"
        else:
            status = "Inconsistent"

        row = [
            id_link,
            type_name,
            mark_val
        ] + per_view_yesno + [status]

        all_rows.append(row)
        if status == "Inconsistent":
            inconsistent_rows.append(row)

    # Build dynamic column names: one per selected view
    view_column_names = [v.Name for v in selected_views]

    base_columns = ["Door Id", "Type", "Mark"]
    final_columns = base_columns + view_column_names + ["Status"]

    # I print the results in the pyRevit output window.
    output.print_md("## Door tag presence in selected views")

    # Quick reminder of which views are included
    output.print_md("Checked views: " + ", ".join(view_column_names))

    output.print_md("### Doors with inconsistent tagging")
    if inconsistent_rows:
        output.print_table(
            table_data=inconsistent_rows,
            columns=final_columns
        )
    else:
        output.print_md("No inconsistencies found.")

    output.print_md("### All doors summary")
    output.print_table(
        table_data=all_rows,
        columns=final_columns
    )

    logger.info("Finished checking door tags for " + str(len(all_rows)) + " doors.")



run()
