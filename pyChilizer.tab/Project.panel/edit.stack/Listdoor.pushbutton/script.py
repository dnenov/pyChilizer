__title__ = 'Door Tag Checker'
__doc__ = 'Analyse if doors are tagged in views and check for inconsistencies.'


from pyrevit import revit, DB, script

doc = revit.doc
logger = script.get_logger()
output = script.get_output()


def safe_name(elem, fallback=""):
    # I want to get a readable name for an element.
    # If the element has no Name property, I return a fallback string.
    if not elem:
        return fallback
    try:
        return elem.Name
    except:
        try:
            return str(elem.Id)
        except:
            return fallback


def get_views_of_type(vtype):
    # I get all non-template views of a given type.
    # For example all floor plans or all elevations.
    views = []
    allviews = DB.FilteredElementCollector(doc) \
                 .OfClass(DB.View) \
                 .ToElements()
    for v in allviews:
        if v.IsTemplate:
            continue
        if v.ViewType == vtype:
            views.append(v)
    return views


def get_doors():
    # I collect all door instances in the whole project.
    doors = DB.FilteredElementCollector(doc) \
              .OfClass(DB.FamilyInstance) \
              .OfCategory(DB.BuiltInCategory.OST_Doors) \
              .WhereElementIsNotElementType() \
              .ToElements()
    return doors


def get_mark_value(door):
    # I read the Mark parameter on a door (if it exists).
    try:
        p = door.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        if p:
            s = p.AsString()
            if s:
                return s
            s2 = p.AsValueString()
            if s2:
                return s2
    except:
        pass
    return ""


def get_referenced_elements_from_tag(tag):
    """
    I try multiple methods to get the elements this tag is attached to. (Not sure everything is necessary)
    I return a list of Element objects (not ElementId).
    """
    elements = []

    # GetTaggedLocalElements 
    try:
        local_elems = tag.GetTaggedLocalElements()
        if local_elems:
            for e in local_elems:
                # Sometimes this already returns elements.
                # Sometimes it returns ids. I do both.
                try:
                    if isinstance(e, DB.Element):
                        elements.append(e)
                        continue
                except:
                    pass
                try:
                    if isinstance(e, DB.ElementId):
                        elem = doc.GetElement(e)
                        if elem:
                            elements.append(elem)
                except:
                    pass
            if elements:
                return elements
    except:
        pass

    #GetTaggedLocalElementIds (if available)
    try:
        local_ids = tag.GetTaggedLocalElementIds()
        if local_ids:
            for eid in local_ids:
                try:
                    elem = doc.GetElement(eid)
                    if elem:
                        elements.append(elem)
                except:
                    pass
            if elements:
                return elements
    except:
        pass

    # GetTaggedElementIds (multi reference style)
    try:
        ref_ids = []
        refs = tag.GetTaggedElementIds()
        if refs:
            for r in refs:
                try:
                    eid = r.ElementId
                    if eid and eid != DB.ElementId.InvalidElementId:
                        ref_ids.append(eid)
                except:
                    pass
        for eid in ref_ids:
            try:
                elem = doc.GetElement(eid)
                if elem:
                    elements.append(elem)
            except:
                pass
        if elements:
            return elements
    except:
        pass

    # TaggedElementId (single reference)
    try:
        ref = tag.TaggedElementId
        if ref and ref.ElementId and ref.ElementId != DB.ElementId.InvalidElementId:
            elem = doc.GetElement(ref.ElementId)
            if elem:
                elements.append(elem)
                return elements
    except:
        pass

    # If nothing works, I return an empty list.
    return elements


def get_tagged_door_ids_in_views(views, door_id_set):
    """
    For a list of views, I find which doors are tagged at least once.
    I return a set of door ids.
    """
    tagged_door_ids = set()

    for view in views:
        # I get all tags in this view.
        tags = DB.FilteredElementCollector(doc, view.Id) \
                 .OfClass(DB.IndependentTag) \
                 .WhereElementIsNotElementType() \
                 .ToElements()

        for tag in tags:
            tagged_elems = get_referenced_elements_from_tag(tag)

            for elem in tagged_elems:
                # I only care about elements whose id is in my door set.
                try:
                    elem_id = elem.Id
                except:
                    continue

                if elem_id in door_id_set:
                    tagged_door_ids.add(elem_id)

    return tagged_door_ids


def run():
    # Main entry point when I click the pychilizer button.

    doors = get_doors()
    if not doors:
        output.print_md("No doors found in the model.")
        return

    # store all door ids in a set so I can test quickly.
    door_ids = set(d.Id for d in doors)

    # I get all floor plans and all elevations.
    plan_views = get_views_of_type(DB.ViewType.FloorPlan)
    elev_views = get_views_of_type(DB.ViewType.Elevation)

    # For plans: which doors have at least one tag in any plan view.
    doors_tagged_in_plans = get_tagged_door_ids_in_views(plan_views, door_ids)

    # For elevations: which doors have at least one tag in any elevation view.
    doors_tagged_in_elevs = get_tagged_door_ids_in_views(elev_views, door_ids)

    all_rows = []
    inconsistent_rows = []

    for door in doors:
        did = door.Id
        id_link = output.linkify(did)

        type_elem = doc.GetElement(door.GetTypeId())
        type_name = safe_name(type_elem, "No Type")

        level_elem = doc.GetElement(door.LevelId)
        level_name = safe_name(level_elem, "")

        mark_val = get_mark_value(door)

        plan_tagged = did in doors_tagged_in_plans
        elev_tagged = did in doors_tagged_in_elevs

        plan_text = "Yes" if plan_tagged else "No"
        elev_text = "Yes" if elev_tagged else "No"

        # If both sides match (both tagged or both not tagged), I say OK.
        # If one is tagged and the other is not, it says Inconsistent.
        if plan_tagged == elev_tagged:
            status = "OK"
        else:
            status = "Inconsistent"

        row = [
            id_link,
            type_name,
            level_name,
            mark_val,
            plan_text,
            elev_text,
            status
        ]

        all_rows.append(row)
        if status == "Inconsistent":
            inconsistent_rows.append(row)

    # I print the results in the pyRevit output window.
    output.print_md("## Door tag presence in plans and elevations")

    output.print_md("### Doors with inconsistent tagging")
    if inconsistent_rows:
        output.print_table(
            table_data=inconsistent_rows,
            columns=["Door Id", "Type", "Level", "Mark", "Tagged in plans", "Tagged in elevations", "Status"]
        )
    else:
        output.print_md("No inconsistencies found.")

    output.print_md("### All doors summary")
    output.print_table(
        table_data=all_rows,
        columns=["Door Id", "Type", "Level", "Mark", "Tagged in plans", "Tagged in elevations", "Status"]
    )

    logger.info("Finished checking door tags for " + str(len(all_rows)) + " doors.")


run()