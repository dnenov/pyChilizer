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