"""Monify UI backend."""
#pylint: disable=E0401,C0103
from pyrevit import forms, revit, DB
from pyrevit import script
from pyrevit.coreutils import ribbon


mlogger = script.get_logger()

doc = __revit__.ActiveUIDocument.Document

DIMGRIDSUI_ENV_VAR = 'DIMGRIDSUIACTIVE'


class TabOption(forms.TemplateListItem):
    def __init__(self, uitab, hidden_tabs_list):
        super(TabOption, self).__init__(uitab)
        self.state = self.name in hidden_tabs_list

    @property
    def name(self):
        return self.item.name


def set_dimgridsui_config(hidden_tabs_list, config):
    config.hidden_tabs = hidden_tabs_list
    script.save_config()


def get_dimgridsui_config(config):
    return config.get_option('hidden_tabs', [])


def config_dimgridsui(config):
    dim_types = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Dimensions).WhereElementIsElementType().ToElements()

    this_ext_name = script.get_extension_name()
    hidden_tabs = get_dimgridsui_config(config)
    tabs = forms.SelectFromList.show(
        [TabOption(doc.GetElement(dim).Name, None) for dim in dim_types],
        title='Dimgrids UI Config',
        button_name='Dimension grids in bulk',
        multiselect=True
        )

    if tabs:
        set_dimgridsui_config([x.name for x in tabs if x], config)


def update_ui(config):
    # Minify or unminify the ui here
    hidden_tabs = get_dimgridsui_config(config)
    for tab in ribbon.get_current_ui():
        if tab.name in hidden_tabs:
            # not new state since the visible value is reverse
            tab.visible = not script.get_envvar(DIMGRIDSUI_ENV_VAR)


def toggle_minifyui(config):
    new_state = not script.get_envvar(DIMGRIDSUI_ENV_VAR)
    script.set_envvar(DIMGRIDSUI_ENV_VAR, new_state)
    script.toggle_icon(new_state)
    update_ui(config)
