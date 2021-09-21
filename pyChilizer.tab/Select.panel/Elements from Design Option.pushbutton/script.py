__title__ = "Select by\nDesign Option"
__doc__ = "All elements from a Design Option. Useful before deleting the design option."

from pyrevit import revit, DB, UI
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
import sys


def get_full_option_name(design_option):
    do_set = design_option.get_Parameter(DB.BuiltInParameter.DESIGN_OPTION_PARAM).AsString()
    do_name = design_option.Name
    do_full_name = " : ".join([do_set, do_name])
    return do_full_name

design_options = DB.FilteredElementCollector(revit.doc).OfClass(DB.DesignOption).ToElements()

do_dict = {get_full_option_name(do) : do for do in design_options}

# construct rwp UI
components = [
    Label("Select Design Option:"),
    ComboBox(name="design_option", options = do_dict),
    Button("Select")]
form = FlexForm("Select Elements by Design Option", components)
form.show()
# assign chosen parameters
chosen_do = form.values["design_option"]

if not chosen_do:
    sys.exit()


selection = revit.get_selection()

selSet = []

do_filter = DB.ElementDesignOptionFilter(chosen_do.Id)
do_el_list = DB.FilteredElementCollector(revit.doc).WherePasses(do_filter).ToElementIds()

for elid in do_el_list:
    selSet.append(elid)

selection.set_to(selSet)
revit.uidoc.RefreshActiveView()