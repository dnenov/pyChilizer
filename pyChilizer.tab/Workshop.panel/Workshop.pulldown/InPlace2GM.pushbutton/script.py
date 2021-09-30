__title__ = "InPlace 2 Loadable"

from pyrevit import revit, DB, UI, HOST_APP, forms, script
from collections import defaultdict
import tempfile
from pyrevit.revit.db import query
from pyrevit.framework import List


def get_fam(some_name, category=DB.BuiltInCategory.OST_GenericModel):
    # get family by given name
    fam_name_filter = query.get_biparam_stringequals_filter({DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM: some_name})
    found_fam = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(category) \
        .WherePasses(fam_name_filter) \
        .WhereElementIsNotElementType().ToElements()
    return found_fam


def convert_length_to_internal(from_units):
    # convert length units from project  to internal
    d_units = DB.Document.GetUnits(revit.doc).GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
    converted = DB.UnitUtils.ConvertToInternalUnits(from_units, d_units)
    return converted


def get_ref_lvl_plane (family_doc):
    # from given family doc, return Ref. Level reference plane
    find_planes = DB.FilteredElementCollector(family_doc).OfClass(DB.SketchPlane)
    return [plane for plane in find_planes if plane.Name == "Ref. Level"]


def get_subcat_name(element):

    subcat_id = element.GraphicsStyleId
#    print (subcat_id)
    if str(subcat_id) != "-1" :
#        print ("yeah")
        return revit.doc.GetElement(subcat_id).Name
    else:
#        print ("nah")
        return None


logger = script.get_logger()

# try use selected elements
selected_elements = revit.get_selection().elements
if len(selected_elements) == 1 and forms.alert("Use selected elements?",
                                               yes=True, no=True):
    source_element = selected_elements[0]
else:
    # get in-place element(select)
    with forms.WarningBar(title="Pick source in-place object:"):
        source_element = revit.pick_element()

forms.alert_ifnot(source_element.Symbol.Family.IsInPlace, "The selected element is not InPlace.", exitscript=True)

#TODO: disable selection of elements not InPlace


def get_inverted_transform_by_bb(geometry_el):
    # get an inverted transform of an element in reference to Bounding Box Min
    bb = geometry_el.GetBoundingBox()
    orig_cs = bb.Transform
    translated_cs = orig_cs.CreateTranslation(bb.Min)
    transform = translated_cs.Inverse
    return transform


def get_bb_min(geo):
    bb = geo.GetBoundingBox()
    return bb.Min


solids_dict = {}
# get DB.GeometryElement
geo_element = source_element.get_Geometry(DB.Options())
family_origin = get_bb_min(geo_element)

# bb = geo_element.GetBoundingBox()
# #family_origin = bb.Min
# orig_cs = bb.Transform
# translated_cs = orig_cs.CreateTranslation(bb.Min)
# transform = translated_cs.Inverse



# TODO: copy material - not possible
# TODO: assign subcategory
# TODO: see what happens with non-Solid elements
# TODO: change category by

# iterate through DB.GeometryInstance and get all geometry, store it in a dictionary with Subcategory name
for instance_geo in geo_element:
    # get DB.GeometryElement
    geometry_element = instance_geo.GetInstanceGeometry()
    for geo in geometry_element:
        # discard elements with 0 volume
        if geo.Volume >0:
            new_solid = DB.SolidUtils.CreateTransformed(geo, get_inverted_transform_by_bb(geo))
            solids_dict[geo] = get_subcat_name(geo)

# TODO: Include more categories
fam_template_path = "C:\ProgramData\Autodesk\RVT " + \
                    HOST_APP.version + "\Family Templates\English\Metric Generic Model.rft"


# define new family doc
try:
    new_family_doc = revit.doc.Application.NewFamilyDocument(fam_template_path)
except:
    forms.alert(msg="No Template",
                sub_msg="There is no Generic Model Template",
                ok=True,
                warn_icon=True, exitscript=True)

# construct family and family type names:
fam_name = source_element.Symbol.Family.Name
# replace spaces (can cause errors)
fam_name = fam_name.strip(" ")
#fam_type_name = fam_name

# if family under this name exists, keep adding Copy 1
if get_fam(fam_name):
    while get_fam(fam_name):
        fam_name = fam_name + "_Copy 1"

# Save family in temp folder
fam_path = tempfile.gettempdir() + "/" + fam_name + ".rfa"
saveas_opt = DB.SaveAsOptions()
saveas_opt.OverwriteExistingFile = True
new_family_doc.SaveAs(fam_path, saveas_opt)

# Load Family into project
with revit.Transaction("Load Family", revit.doc):
    try:
        loaded_f = revit.db.create.load_family(fam_path, doc=revit.doc)
        revit.doc.Regenerate()
    except Exception as err:
        logger.error(err)


#new_geo_collection = []
# Copy geometry from In-Place to Loadable family

#parent_cat = DB.Category(DB.BuiltInCategory.OST_GenericModel)

with revit.Transaction(doc=new_family_doc, name="Copy Geometry"):

    parent_cat = new_family_doc.OwnerFamily.FamilyCategory
    #print(parent_cat)
   # new_subcat = new_family_doc.Settings.Categories.NewSubcategory(parent_cat, "new_cat")

    for geo in solids_dict.keys():
        # if the geometry has a subcategory name
        if solids_dict[geo]:
            #print ("yes")
            # check if the subcategory exists
            check_if_exists = new_family_doc.Settings.Categories.Contains(solids_dict[geo])
            # if yes, select subcategory by name
            if check_if_exists:
                subcat = [cat for cat in new_family_doc.Categories if cat.Name == solids_dict[geo]]
            # if not create subcategory using parent category and string (name)
            else:
                subcat = new_family_doc.Settings.Categories.NewSubcategory(parent_cat, solids_dict[geo])

            # create freeform element (copy of the geometry))
            copied_geo = DB.FreeFormElement.Create(new_family_doc, geo)

            # assign subcategory
            copied_geo.Subcategory = subcat
        else:
            # not
            print ("no, not sure what happens here")
            print (solids_dict[geo])

    new_family_doc.Regenerate()

# save and close family
save_opt = DB.SaveOptions()
new_family_doc.Save(save_opt)
new_family_doc.Close()


# non-structural type to place family instance
str_type = DB.Structure.StructuralType.NonStructural

# Reload family and place it in the same position as the original element
with revit.Transaction("Reload Family", revit.doc):

    loaded_f = revit.db.create.load_family(fam_path, doc=revit.doc)
    revit.doc.Regenerate()

    # find family symbol and activate
    fam_symbol = None
    get_fam = DB.FilteredElementCollector(revit.doc).OfClass(DB.FamilySymbol).OfCategory(
        DB.BuiltInCategory.OST_GenericModel).WhereElementIsElementType().ToElements()

    for fam in get_fam:
        type_name = fam.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
        if str.strip(type_name) == fam_name:
            fam_symbol = fam
            fam_symbol.Name = fam_name

            if not fam_symbol.IsActive:
                fam_symbol.Activate()
                revit.doc.Regenerate()

            # place family symbol at postision
            new_fam_instance = revit.doc.Create.NewFamilyInstance(family_origin, fam_symbol, str_type)



