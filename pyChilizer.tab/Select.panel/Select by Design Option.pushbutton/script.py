__title__ = "Select by Design Option"
__doc__ = "Select elements of a design option"


from pyrevit import revit, DB, UI, forms
from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button)
import sys


def get_full_option_name(design_option):
    do_set_id = design_option.get_Parameter(DB.BuiltInParameter.OPTION_SET_ID).AsElementId()
    do_set = revit.doc.GetElement(do_set_id).Name
    do_name = design_option.Name
    do_full_name = " : ".join([do_set, do_name])
    return do_full_name


design_options = DB.FilteredElementCollector(revit.doc).OfClass(DB.DesignOption).ToElements()
forms.alert_ifnot(design_options, "No Design Options in model.", exitscript=True)
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

forms.alert_ifnot(do_el_list, "No elements in Design Option:\n {}".format(chosen_do.Name), exitscript=True)

for elid in do_el_list:
    selSet.append(elid)

selection.set_to(selSet)
revit.uidoc.RefreshActiveView()