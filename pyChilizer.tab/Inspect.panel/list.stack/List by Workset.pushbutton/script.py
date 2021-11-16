__title__ = "List by Workset"
__doc__ = "List numbers of elements of project's Worksets, broken down by category."

from pyrevit import revit, DB, UI, forms
from collections import defaultdict


def get_elements_by_workset(w, doc=revit.doc):
    # quickly collect element belonging to a Workset
    # quick filter
    w_filter = DB.ElementWorksetFilter(w.Id)
    # collect with Design Option filter
    w_el_list = DB.FilteredElementCollector(doc) \
        .WherePasses(w_filter) \
        .WhereElementIsNotElementType() \
        .ToElements()
    return w_el_list

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
worksets = DB.FilteredWorksetCollector(revit.doc).OfKind(DB.WorksetKind.UserWorkset).ToWorksets()
# exit in no DO
forms.alert_ifnot(worksets, "No Worksets in model.", exitscript=True)

for w in worksets:
    # get all elements in DO
    all_in_w = get_elements_by_workset(w)

    if all_in_w:

        element_categories = defaultdict(list)
        counter = 0
        # count elements by category
        for elem in all_in_w:
            try:
                cat_name = elem.Category.Name
                cat_id = elem.Category.Id.IntegerValue
                if cat_id <0 and cat_id not in cat_ban_list:
                    element_categories[cat_name].append(elem)
                    counter += 1
            except:
                #print (elem.Name, elem.Id)
                pass

        print('\n \n WORKSET: {} '.format(w.Name))
        print("\t\t\t Breakdown by Category:")
        for category in element_categories:
            print ("\t\t\t ........{} : {}".format(category, str(len(element_categories[category]))))
        print ("\t\t\t TOTAL : {} elements".format(counter))

    else:
        print("\n \n OPTION: {} EMPTY".format(w.Name))