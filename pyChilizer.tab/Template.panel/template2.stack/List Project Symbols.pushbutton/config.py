"""List Project Symbols tool config

"""

from pyrevit import revit, script, DB, forms

config = script.get_config()
custom_config = script.get_config("List Project Symbolsconfig")


# list of symbol categories
categories = [
    DB.BuiltInCategory.OST_DoorTags,
    DB.BuiltInCategory.OST_WindowTags,
    DB.BuiltInCategory.OST_RoomTags,
    DB.BuiltInCategory.OST_AreaTags,
    DB.BuiltInCategory.OST_WallTags,
    DB.BuiltInCategory.OST_CurtainWallPanelTags,
    DB.BuiltInCategory.OST_SectionHeads,
    DB.BuiltInCategory.OST_CalloutHeads,
    DB.BuiltInCategory.OST_CeilingTags,
    DB.BuiltInCategory.OST_FurnitureTags,
    DB.BuiltInCategory.OST_PlumbingFixtureTags,
    DB.BuiltInCategory.OST_ReferenceViewerSymbol,
    DB.BuiltInCategory.OST_GridHeads,
    DB.BuiltInCategory.OST_LevelHeads,
    DB.BuiltInCategory.OST_SpotElevSymbols,
    DB.BuiltInCategory.OST_ElevationMarks,
    DB.BuiltInCategory.OST_StairsTags,
    DB.BuiltInCategory.OST_StairsLandingTags,
    DB.BuiltInCategory.OST_StairsRunTags,
    DB.BuiltInCategory.OST_StairsSupportTags,
    DB.BuiltInCategory.OST_BeamSystemTags,
    DB.BuiltInCategory.OST_StructuralFramingTags,
    DB.BuiltInCategory.OST_ViewportLabel
]

class PREVCategoryItem(forms.TemplateListItem):
    pass



def load_config():
    prev_cats = custom_config.get_option("chosen_categories", [])
    revit_cats = [revit.query.get_category(x) for x in prev_cats]
    return revit_cats

def config_categories():

    prev_cats = load_config()
    prev_catnames = [x.Name for x in prev_cats]
    reformat_cats = [revit.query.get_category(x) for x in categories]
    chosen_categories = forms.SelectFromList.show(
        sorted(
            [PREVCategoryItem(x,
                              checked=x.Name in prev_catnames,
                              name_attr="Name") for x in reformat_cats],
            key=lambda x : x.name),
            title = "Select Categories",
            button_name="Apply",
            multiselect=True)
    if chosen_categories:
        save_config(chosen_categories)
    return chosen_categories

def save_config(cats):
    custom_config.chosen_categories = [x.Name for x in cats]
    script.save_config()

def get_categories():
    chosen_cat_names = config.get_option("chosen_categories", [])
    categories = [revit.query.get_builtincategory(x) for x in chosen_cat_names]
    return categories


if __name__ == "__main__":
    config_categories()
