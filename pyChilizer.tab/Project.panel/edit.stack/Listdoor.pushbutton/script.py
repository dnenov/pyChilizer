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

# Instead of:
# plan_views = get_views_of_type(...)
# elev_views = get_views_of_type(...)

plan_views, elev_views = select_views()
if not plan_views and not elev_views:
    return  # user cancelled or no valid views

door_ids = set(d.Id for d in doors)

doors_tagged_in_plans = get_tagged_door_ids_in_views(plan_views, door_ids) if plan_views else set()
doors_tagged_in_elevs = get_tagged_door_ids_in_views(elev_views, door_ids) if elev_views else set()
