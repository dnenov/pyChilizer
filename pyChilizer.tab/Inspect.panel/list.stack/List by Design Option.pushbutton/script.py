__title__ = "List by Design Option"
__doc__ = "List numbers of elements of project's Design Options, broken down by category."

from pyrevit import revit, DB, UI, forms
from pyrevit.compat import get_elementid_value_func
from collections import defaultdict

get_elementid_value = get_elementid_value_func()

def get_elements_by_do(do, doc=revit.doc):
    # quickly collect element belonging to a Design Option
    # quick filter
    do_filter = DB.ElementDesignOptionFilter(do.Id)
    # collect with Design Option filter
    do_el_list = DB.FilteredElementCollector(doc).WherePasses(do_filter).WhereElementIsNotElementType().ToElements()
    return do_el_list


def get_full_option_name(design_option):
    # get full design option name consisting of the set name + option name
    do_set_id = design_option.get_Parameter(DB.BuiltInParameter.OPTION_SET_ID).AsElementId()
    do_set = revit.doc.GetElement(do_set_id).Name
    do_name = design_option.Name
    do_full_name = " - ".join([do_set, do_name])
    return do_full_name

# list of categories irrelevant for count
cat_ban_list = [
    -2000260,   # dimensions
    -2000261,   # Automatic Sketch Dimensions
    -2000954,   # railing path extension lines
    -2000045,   # <Sketch>
    -2000067,   # <Stair/Ramp Sketch: Boundary>
    -2000262,   # Constraints
    -2000920,   # Landings
    -2000919,   # Stair runs
    -2000123,   # Supports
    -2000173,   # curtain wall grids
    -2000171,   # curtain wall mullions
    -2000170,   # curtain panels
    -2000530,   # reference places
    -2000127,   # Balusters
    -2000947,   # Handrail
    -2000946,   # Top Rail
]

# get DO in model
design_options = DB.FilteredElementCollector(revit.doc).OfClass(DB.DesignOption).ToElements()
# exit in no DO
forms.alert_ifnot(design_options, "No Design Options in model.", exitscript=True)

# create dict of name and DO element
do_dict = {get_full_option_name(do): do for do in design_options}

for do_full_name, do in do_dict.items():
    # get all elements in DO
    all_in_do = get_elements_by_do(do)

    if all_in_do:

        element_categories = defaultdict(list)
        counter = 0
        # count elements by category
        for elem in all_in_do:
            try:
                cat_name = elem.Category.Name
                cat_id = get_elementid_value(elem.Category.Id)
                if cat_id <0 and cat_id not in cat_ban_list:
                    element_categories[cat_name].append(elem)
                    counter += 1
            except:
                #print (elem.Name, elem.Id)
                pass

        print('\n \n OPTION: {} '.format(do_full_name))
        print("\t\t\t Breakdown by Category:")
        for category in element_categories:
            print ("\t\t\t ........{} : {}".format(category, str(len(element_categories[category]))))
        print ("\t\t\t TOTAL : {} elements".format(counter))

    else:
        print("\n \n OPTION: {} EMPTY".format(do_full_name))