from pyrevit import script, revit, DB

selection = revit.get_selection()


if not selection.is_empty:
    el = revit.doc.GetElement(selection.first.Id)
    try:
        group_id = el.GroupId
        selection = selection.set_to(group_id)
    except AttributeError:
        print ("Element is not part of any Group.")