__title__ = "Select by\nDesign Option"
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


def get_elements_by_do(do, doc=revit.doc):
    # quickly collect element belonging to a Design Option
    # quick filter
    do_filter = DB.ElementDesignOptionFilter(do.Id)
    # collect with Design Option filter
    do_el_list = DB.FilteredElementCollector(doc).WherePasses(do_filter).ToElements()
    return do_el_list


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

# collect elements belonging to chosen Design Option
do_el_list = get_elements_by_do(chosen_do)
# exit script if no elements found
forms.alert_ifnot(do_el_list, "No elements in Design Option:\n {}".format(chosen_do.Name), exitscript=True)

# add element
selection = revit.get_selection()
selSet = [elid.Id for elid in do_el_list]

selection.set_to(selSet)
revit.uidoc.RefreshActiveView()