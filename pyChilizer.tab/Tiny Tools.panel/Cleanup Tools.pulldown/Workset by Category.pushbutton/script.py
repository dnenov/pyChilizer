__title__ = "Workset by Category"
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
}


# Check model is workshared
if forms.check_workshared(revit.doc, 'Model is not workshared.'):
    # Check all elements are ungrouped
    if check_ungrouped():

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

                        counter = 0
                        for w in coll_elements:
                            # for each element get workset parameter
                            w_param = w.get_Parameter(DB.BuiltInParameter.ELEM_PARTITION_PARAM)
                            if not w_param.IsReadOnly: # don't touch elements with read-only parameter
                                try:
                                    w_param.Set(ws.Id.IntegerValue) # set workset
                                    counter += 1
                                finally:
                                    pass
                        # annotate process
                        print("Sorted {} elements to workset {}".format(counter, ws.Name))