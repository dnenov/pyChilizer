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