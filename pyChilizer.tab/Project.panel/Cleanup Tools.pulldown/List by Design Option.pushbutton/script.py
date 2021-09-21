__title__ = "List by Design Option"

from pyrevit import revit, DB, UI, forms
from collections import defaultdict


def get_elements_by_do(do, doc=revit.doc):
    # quickly collect element belonging to a Design Option
    # quick filter
    do_filter = DB.ElementDesignOptionFilter(do.Id)
    # collect with Design Option filter
    do_el_list = DB.FilteredElementCollector(doc).WherePasses(do_filter).ToElements()
    return do_el_list


def get_full_option_name(design_option):
    do_set_id = design_option.get_Parameter(DB.BuiltInParameter.OPTION_SET_ID).AsElementId()
    do_set = revit.doc.GetElement(do_set_id).Name
    do_name = design_option.Name
    do_full_name = " - ".join([do_set, do_name])
    return do_full_name


design_options = DB.FilteredElementCollector(revit.doc).OfClass(DB.DesignOption).ToElements()

forms.alert_ifnot(design_options, "No Design Options in model.", exitscript=True)
do_dict = {get_full_option_name(do): do for do in design_options}

for do_full_name, do in do_dict.items():
    all_in_do = get_elements_by_do(do)
    if all_in_do:
        #print('\n' + '{} : {} elements total'.format(do_full_name, len(all_in_do)))
        element_categories = defaultdict(list)
        counter = 0
        #print('\n' + '{}'.format(do_full_name))

        # count elements by category
        for elem in all_in_do:
            counter += 1
            try:
                element_categories[elem.Category.Name].append(elem)
            except:
                #print (elem.Name, elem.Id)
                pass

        print('\n OPTION: {} - {} elements total'.format(do_full_name, len(all_in_do)))
        print("\t\t\t By Category:")
        for category in element_categories:
            print ("\t\t\t ________{} : {}".format(category, str(len(element_categories[category]))))
