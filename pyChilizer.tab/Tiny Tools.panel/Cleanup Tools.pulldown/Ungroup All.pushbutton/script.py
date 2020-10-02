__title__ = "Ungroup \n all"
__doc__ = "Ungroups all groups in project"

from pyrevit import revit, DB, script, forms

output = script.get_output()
# Gather groups
coll_groups = DB.FilteredElementCollector(revit.doc) \
    .OfClass(DB.Group) \
    .WhereElementIsNotElementType() \
    .ToElements()
ungr_ids=[]
if coll_groups:
    with revit.Transaction ("Ungroup All", revit.doc):
        print("UNGROUPED {} GROUPS:".format(len(coll_groups)))
        for gr in coll_groups:
            ungrouped = (gr.UngroupMembers())
            print ("\n")
            print("{} \t {} ".format(gr.Name,output.linkify(gr.Id)))
else:
    print("No groups in project")

