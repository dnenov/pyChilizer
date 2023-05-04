from collections import defaultdict
from pyrevit import HOST_APP
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script
import random
import threedconfig
from pychilizer import database, colorize
from pyrevit.framework import List


logger = script.get_logger()
BIC = DB.BuiltInCategory
doc = revit.doc
overrides_option = threedconfig.get_config()
solid_fill_pattern = database.get_solid_fill_pat(doc=doc)

# colour gradients solution by https://bsouthga.dev/posts/color-gradients-with-python

# [x] revise colours to exclude nearby colours
# [x] include more categories
# [x] set view to open active
# [-] include which types to colorize - unclear if useful
# [x] test in R2022 R2023
# [-] work with links? - cannot override
# [x] fix dependency on the initial 3D view


category_opt_dict = {
    "Windows": BIC.OST_Windows,
    "Doors": BIC.OST_Doors,
    "Floors": BIC.OST_Floors,
    "Walls": BIC.OST_Walls,
    "Generic Model": BIC.OST_GenericModel,
    "Casework": BIC.OST_Casework,
    "Furniture": BIC.OST_Furniture,
    "Furniture Systems": BIC.OST_FurnitureSystems,
    "Electrical Equipment":BIC.OST_ElectricalEquipment,
    "Electrical Fixtures":BIC.OST_ElectricalFixtures,
    "Parking":BIC.OST_Parking,
    "Site":BIC.OST_Site,
    "Entourage":BIC.OST_Entourage,
    "Plumbing Fixtures": BIC.OST_PlumbingFixtures,
    "Roofs": BIC.OST_Roofs,
    "Specialty Equipment": BIC.OST_SpecialityEquipment,
    "Ceilings": BIC.OST_Ceilings,
    "Curtain Wall Panels": BIC.OST_CurtainWallPanels,
    "Curtain Wall Mullions": BIC.OST_CurtainWallMullions,
    "Topography":BIC.OST_Topography,
    "Structural Columns":BIC.OST_StructuralColumns,
    "Structural Framing":BIC.OST_StructuralFraming,
    "Stairs":BIC.OST_Stairs,
    "Ramps":BIC.OST_Ramps,

}
sorted_cats = sorted(category_opt_dict.keys(), key=lambda x:x)

selected_cat = forms.CommandSwitchWindow.show(sorted_cats, message="Select Category to Colorize", width = 400)
if selected_cat == None:
    script.exit()

chosen_bic = [category_opt_dict[selected_cat]]
if selected_cat in ["Curtain Wall Panels", "Curtain Wall Mullions"]: # not so elegant way to support curtain panels by adding walls category
    chosen_bic.append(BIC.OST_Walls)

# get all element categories and return a list of all categories except chosen BIC
all_cats = doc.Settings.Categories
chosen_category = [all_cats.get_Item(i) for i in chosen_bic]
hide_categories_except = [c for c in all_cats if c.Id not in [i.Id for i in chosen_category]]

with revit.Transaction("Create Colorized 3D"):
    view_name = "Colorize {} by Type".format(selected_cat)
    if database.delete_existing_view(view_name, doc=doc):
        # create new 3D
        viewtype_id = database.get_3Dviewtype_id(doc=doc)
        database.remove_viewtemplate(viewtype_id, doc=doc)
        view = DB.View3D.CreateIsometric(doc, viewtype_id)
        view.Name = view_name

    # hide other categories
    for cat in hide_categories_except:
        if view.CanCategoryBeHidden(cat.Id):
            view.SetCategoryHidden(cat.Id, True)

    get_view_elements = DB.FilteredElementCollector(doc) \
        .OfCategory(chosen_bic[0]) \
        .WhereElementIsNotElementType() \
        .ToElements()

    # for special cases with Curtain Wall Mullions or Curtain View Panel - hide walls that are not Panels
    if selected_cat in ["Curtain Wall Panels", "Curtain Wall Mullions"]:
        # get all walls that are not panels (their category will be == Walls)
        get_wall_elements = DB.FilteredElementCollector(doc)\
                            .OfCategory(BIC.OST_Walls) \
                            .WhereElementIsNotElementType() \
                                .ToElements()
        # filter the walls that are not Curtain Walls and hide them
        not_cw_elements = List[DB.ElementId]([w.Id for w in get_wall_elements if w.WallType.Kind != DB.WallKind.Curtain ])
        view.HideElements(not_cw_elements)

types_dict = defaultdict(set)
for el in get_view_elements:

    # discard nested shared - group under the parent family
    if selected_cat in ["Floors", "Walls", "Roofs", "Ceilings"]:
        type_id = el.GetTypeId()
    else:
        try:
            type_id = el.SuperComponent.GetTypeId()
        except:
            type_id = el.GetTypeId()
    types_dict[type_id].add(el.Id)

# colour dictionary
n = len(types_dict)

if n < 14:
    colours = colorize.basic_colours()
else:
    colours = colorize.rainbow()
col_dict = colorize.polylinear_gradient(colours, n)
chop_col_list = col_dict["hex"][0:n]

revit_colours = [colorize.revit_colour(h) for h in chop_col_list]
for x in range(10):
    random.shuffle(revit_colours)

with revit.Transaction("Isolate and Colorize Types"):
    for type_id, c in zip(types_dict.keys(), revit_colours):
        type_instance = types_dict[type_id]
        override = DB.OverrideGraphicSettings()
        if "Projection Line Colour" in overrides_option:
            override.SetProjectionLineColor(c)
        if "Cut Line Colour" in overrides_option:
            override.SetCutLineColor(c)
        if "Projection Surface Colour" in overrides_option:
            override.SetSurfaceForegroundPatternColor(c)
            override.SetSurfaceForegroundPatternId(solid_fill_pattern.Id)
        if "Cut Pattern Colour" in overrides_option:
            override.SetCutForegroundPatternColor(c)
            override.SetCutForegroundPatternId(solid_fill_pattern.Id)
        for inst in type_instance:
            view.SetElementOverrides(inst, override)
revit.active_view = view
