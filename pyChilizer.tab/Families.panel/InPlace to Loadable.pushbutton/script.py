__title__ = "InPlace to\nLoadable"
__doc__ = "Transform one In-Place element to a loadable family. Will always use GM category. Subcategories will be respected"


from pyrevit import revit, DB, UI, HOST_APP, forms, script
from collections import defaultdict
import tempfile
from pyrevit.revit.db import query
from pyrevit.framework import List

output = script.get_output()
close_other_output = output.close_others(all_open_outputs=True)


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
    # check if geometry has a subcategory, return Subcategory Name or None
    subcat_id = element.GraphicsStyleId
    if str(subcat_id) != "-1" :
        return revit.doc.GetElement(subcat_id).Name
    else:
        return None


def inverted_transform_by_ref(reference):
    transform = DB.Transform.CreateTranslation(reference)
    return transform.Inverse


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

solids_dict = {}
# get DB.GeometryElement
geo_element = source_element.get_Geometry(DB.Options())
bb = geo_element.GetBoundingBox()
family_origin = bb.Min


# iterate through DB.GeometryInstance and get all geometry, store it in a dictionary with Subcategory name
for instance_geo in geo_element:
    # get DB.GeometryElement
    geometry_element = instance_geo.GetInstanceGeometry()
    for geo in geometry_element:
        # discard elements with 0 volume
        if geo.Volume >0:
            new_solid = DB.SolidUtils.CreateTransformed(geo, inverted_transform_by_ref(bb.Min))
            solids_dict[new_solid] = get_subcat_name(geo)

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
fam_name = "GM_"+source_element.Symbol.Family.Name
# replace spaces (can cause errors)
fam_name = fam_name.strip(" ")

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

# Copy geometry from In-Place to Loadable family
with revit.Transaction(doc=new_family_doc, name="Copy Geometry"):

    parent_cat = new_family_doc.OwnerFamily.FamilyCategory
    new_mat_param = new_family_doc.FamilyManager.AddParameter("Material",
                                                              DB.BuiltInParameterGroup.PG_MATERIALS,
                                                              DB.ParameterType.Material,
                                                              False)

    for geo in solids_dict.keys():
        # create freeform element (copy of the geometry))
        copied_geo = DB.FreeFormElement.Create(new_family_doc, geo)

        # assign material parameter
        try:
            geo_mat_param = copied_geo.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)
            new_family_doc.FamilyManager.AssociateElementParameterToFamilyParameter(geo_mat_param, new_mat_param)
        except Exception as err:
            logger.error(err)
        # if the geometry has a subcategory name
        if solids_dict[geo]:
            # check if the subcategory exists
            check_if_exists = new_family_doc.Settings.Categories.Contains(solids_dict[geo])
            # if yes, select subcategory by name
            if check_if_exists:
                subcat = [cat for cat in new_family_doc.Categories if cat.Name == solids_dict[geo]]
            # if not create subcategory using parent category and string (name)
            else:
                subcat = new_family_doc.Settings.Categories.NewSubcategory(parent_cat, solids_dict[geo])
            # assign subcategory
            copied_geo.Subcategory = subcat
    new_family_doc.Regenerate()

# save and close family
save_opt = DB.SaveOptions()
new_family_doc.Save(save_opt)
new_family_doc.Close()

# non-structural type to place family instance
str_type = DB.Structure.StructuralType.NonStructural

# Reload family and place it in the same position as the original element
with revit.Transaction("Reload Family", revit.doc):
    try:
        loaded_f = revit.db.create.load_family(fam_path, doc=revit.doc)
        revit.doc.Regenerate()
    except Exception as err:
        logger.error(err)
    # find family symbol and activate
    fam_symbol = None
    get_fam = DB.FilteredElementCollector(revit.doc).OfClass(DB.FamilySymbol).WhereElementIsElementType().ToElements()

    for fam in get_fam:
        type_name = fam.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
        if str.strip(type_name) == fam_name:
            fam_symbol = fam
            fam_symbol.Name = fam_name

            if not fam_symbol.IsActive:
                fam_symbol.Activate()
                revit.doc.Regenerate()

            # place family symbol at position
            new_fam_instance = revit.doc.Create.NewFamilyInstance(family_origin, fam_symbol, str_type)

print ("Created and placed family instance : {1} {0} ".format(output.linkify(new_fam_instance.Id), fam_name))

