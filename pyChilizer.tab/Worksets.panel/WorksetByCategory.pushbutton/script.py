__title__ = "Workset\nby Category"
__doc__ = "Appoints elements to worksets by category. Works only with ungrouped elements. Supports only common architectural categories"

from pyrevit import revit, DB, script, forms

def check_ungrouped():
    # Check that all elements have been ungrouped
    coll_groups = DB.FilteredElementCollector(revit.doc) \
        .OfClass(DB.Group) \
        .WhereElementIsNotElementType() \
        .ToElements()
    if coll_groups:
        forms.alert("Ungroup elements first", warn_icon=True)
        return False
    return True


def discard_grouped(elements):
    """discard grouped elements"""
    return [el for el in elements if el.GroupId == DB.ElementId.InvalidElementId and not isinstance(el, DB.Group)]


def count_grouped(els):
    # count how many grouped elements in list
    grouped_els = [el for el in els if not el.GroupId == DB.ElementId.InvalidElementId]
    return len(grouped_els)


cat_dict = {
    "Wall":     DB.BuiltInCategory.OST_Walls,
    "Window":   DB.BuiltInCategory.OST_Windows,
    "Floor":    DB.BuiltInCategory.OST_Floors,
    "Slab":     DB.BuiltInCategory.OST_Floors,
    "Stair":    DB.BuiltInCategory.OST_Stairs,
    "Railing": DB.BuiltInCategory.OST_StairsRailing,
    "Doors":    DB.BuiltInCategory.OST_Doors,
    "Furniture": DB.BuiltInCategory.OST_Furniture,
    "Plumbing": DB.BuiltInCategory.OST_PlumbingFixtures,
    "Roof": DB.BuiltInCategory.OST_Roofs,
    "Ceiling": DB.BuiltInCategory.OST_Ceilings,
    "Topography": DB.BuiltInCategory.OST_Topography
}


# Check model is workshared
if forms.check_workshared(revit.doc, 'Model is not workshared.'):
    # Check all elements are ungrouped


    # Collect all worksets in model with Filtered Workset Collector
    coll_worksets = DB.FilteredWorksetCollector(revit.doc).OfKind(DB.WorksetKind.UserWorkset)

    # Iterate through categories in dictionary

    for keyword in cat_dict:
        with revit.Transaction(keyword, revit.doc):
            for ws in coll_worksets:
                # check for keyword in workset name
                if keyword in ws.Name or keyword.upper() in ws.Name or keyword.lower() in ws.Name:

                    # inverted workset filter - pick up elements that are not in workset
                    ws_filter = DB.ElementWorksetFilter(ws.Id, True)
                    # collect all elements of category
                    coll_elements = DB.FilteredElementCollector(revit.doc) \
                            .OfCategory(cat_dict[keyword]) \
                            .WherePasses(ws_filter) \
                            .WhereElementIsNotElementType() \
                            .ToElements()
                    discarded = count_grouped(coll_elements)
                    coll_not_in_groups = discard_grouped(coll_elements)
                    counter = 0
                    for w in coll_not_in_groups:

                        # for each element get workset parameter
                        w_param = w.get_Parameter(DB.BuiltInParameter.ELEM_PARTITION_PARAM)
                        if not w_param.IsReadOnly: # don't touch elements with read-only parameter
                            try:
                                w_param.Set(ws.Id.IntegerValue) # set workset
                                counter += 1
                            finally:
                                pass
                        # annotate process
                    print("Sorted {} elements to workset {}. {} elements discarded (in groups)".format(counter, ws.Name, discarded))