__title__ = 'Door Tag Checker'
__doc__ = 'Analyse if doors are tagged in selected views and check for inconsistencies.'


from pyrevit import revit, DB, script, forms

doc = revit.doc
logger = script.get_logger()
output = script.get_output()


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
        # "Level 01 - [FloorPlan]"
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
    """

    all_potential_views = get_all_potential_views()

    if not all_potential_views:
        forms.alert("No suitable views found in this model.",
                    title="Door Tag Checker")
        return [], []

    # Group by view type 
    grouped = {}
    for v in all_potential_views:
        try:
            group_name = str(v.ViewType)
        except:
            group_name = "Other"

        if group_name not in grouped:
            grouped[group_name] = []

        grouped[group_name].append(ViewOption(v))

    # Show UI
    selected_views_raw = forms.SelectFromList.show(
        grouped,
        title="Select Views to Check Door Tags",
        button_name="Check Doors",
        multiselect=True
    )

    if not selected_views_raw:
        forms.alert("No views selected.", title="Door Tag Checker")
        return [], []

    # Normalise returned objects
    selected_views = []
    for x in selected_views_raw:
        if isinstance(x, DB.View):
            selected_views.append(x)
        elif hasattr(x, 'item') and isinstance(x.item, DB.View):
            selected_views.append(x.item)

    # Categorise
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


def get_tagged_door_ids_in_views(views, door_ids):
    """
    Get set of door IDs that are tagged in the given views.
    
    Args:
        views: List of View objects to check
        door_ids: Set of door ElementIds to filter (only return IDs in this set)
    
    Returns:
        Set of door ElementIds that are tagged in the views
    """
    tagged_door_ids = set()
    
    for view in views:
        try:
            # Get all door tags in this view
            tags = DB.FilteredElementCollector(doc, view.Id) \
                     .OfCategory(DB.BuiltInCategory.OST_DoorTags) \
                     .ToElements()
            
            for tag in tags:
                try:
                    # Get the tagged element ID
                    if hasattr(tag, 'TaggedElementId'):
                        tagged_id = tag.TaggedElementId
                    elif hasattr(tag, 'TaggedLocalElementId'):
                        tagged_id = tag.TaggedLocalElementId
                    else:
                        # Try to get from the tag's reference
                        refs = tag.GetTaggedReferences()
                        if refs and len(refs) > 0:
                            tagged_id = refs[0].ElementId
                        else:
                            continue
                    
                    # Only include if it's in our door_ids set
                    if tagged_id in door_ids:
                        tagged_door_ids.add(tagged_id)
                except:
                    # Skip tags that can't be processed
                    continue
        except:
            # Skip views that can't be processed
            continue
    
    return tagged_door_ids


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

    # For plans: which doors have at least one tag in any plan view.
    doors_tagged_in_plans = get_tagged_door_ids_in_views(plan_views, door_ids) if plan_views else set()

    # For elevations: which doors have at least one tag in any elevation view.
    doors_tagged_in_elevs = get_tagged_door_ids_in_views(elev_views, door_ids) if elev_views else set()

    all_rows = []
    inconsistent_rows = []

    for door in doors:
        did = door.Id
        id_link = output.linkify(did)

        type_elem = doc.GetElement(door.GetTypeId())
        type_name = safe_name(type_elem, "No Type")

        level_name = ""
        try:
            level_id = door.LevelId
            if level_id and level_id != DB.ElementId.InvalidElementId:
                level_elem = doc.GetElement(level_id)
                level_name = safe_name(level_elem, "")
        except:
            pass

        mark_val = get_mark_value(door)

        plan_tagged = did in doors_tagged_in_plans
        elev_tagged = did in doors_tagged_in_elevs

        plan_text = "Yes" if plan_tagged else "No"
        elev_text = "Yes" if elev_tagged else "No"

        # If both sides match (both tagged or both not tagged), I say OK.
        # If one is tagged and the other is not, it says Inconsistent.
        if plan_tagged == elev_tagged:
            status = "OK"
        else:
            status = "Inconsistent"

        row = [
            id_link,
            type_name,
            view_name,
            mark_val,
            plan_text,
            elev_text,
            status
        ]

        all_rows.append(row)
        if status == "Inconsistent":
            inconsistent_rows.append(row)

    # I print the results in the pyRevit output window.
    output.print_md("## Door tag presence in plans and elevations")

    output.print_md("### Doors with inconsistent tagging")
    if inconsistent_rows:
        output.print_table(
            table_data=inconsistent_rows,
            columns=["Door Id", "Type", "view", "Mark", "Tagged in plans", "Tagged in elevations", "Status"]
        )
    else:
        output.print_md("No inconsistencies found.")

    output.print_md("### All doors summary")
    output.print_table(
        table_data=all_rows,
        columns=["Door Id", "Type", "View", "Mark", "Tagged in plans", "Tagged in elevations", "Status"]
    )

    logger.info("Finished checking door tags for " + str(len(all_rows)) + " doors.")


run()