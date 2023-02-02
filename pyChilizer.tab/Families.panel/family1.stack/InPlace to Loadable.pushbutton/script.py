__title__ = "InPlace to\nLoadable"
__doc__ = "Select an In-Place element to convert into a Loadable family and place in the same location. " \
          "Subcategories will be respected" \
          "Will assign a"

from pyrevit import revit, DB, UI, HOST_APP, forms, script
import tempfile
from pyrevit.revit.db import query
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
output = script.get_output()
from Autodesk.Revit import Exceptions
import rpw
from pychilizer import database, geo

#todo: update languages

def get_fam_by_name_and_cat(some_name, category=DB.BuiltInCategory.OST_GenericModel):
    # get family by given name
    fam_name_filter = database.get_biparam_stringequals_filter({DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM: some_name})
    found_fam = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(category) \
        .WherePasses(fam_name_filter) \
        .WhereElementIsNotElementType().ToElements()
    return found_fam


def sk_plane(curve):
    try:
        p1 = curve.Evaluate(0, True)
    except Exceptions.ArgumentOutOfRangeException:
        return None
    if isinstance(curve, DB.Line):
        p1 = curve.Evaluate(0, True)
        tangent = curve.ComputeDerivatives(0, True).BasisX
        normal = tangent.CrossProduct(p1)
        plane = DB.Plane.CreateByNormalAndOrigin(normal, p1)
        sketch_plane = DB.SketchPlane.Create(new_family_doc, plane)
    else:
        deriv = curve.ComputeDerivatives(1, True)
        normal = deriv.BasisZ.Normalize()
        plane = DB.Plane.CreateByNormalAndOrigin(normal, p1)
        sketch_plane = DB.SketchPlane.Create(new_family_doc, plane)
    return sketch_plane


def get_subcat_name(element):
    # check if geometry has a subcategory, return Subcategory Name or Nones
    subcat_id = element.GraphicsStyleId
    if str(subcat_id) != "-1":
        return revit.doc.GetElement(subcat_id).Name
    else:
        return None


def inverted_transform_by_ref(reference):
    transform = DB.Transform.CreateTranslation(reference)
    return transform.Inverse


logger = script.get_logger()


# selection filter for InPlace elements
class InPlaceFilter(ISelectionFilter):
    def AllowElement(self, elem):
        try:
            if elem.Symbol.Family.IsInPlace:
                return True
            else:
                return False
        except AttributeError:
            return False


def select_inplace_filter():
    # select elements while applying filter
    try:
        with forms.WarningBar(title="Select In-Place element to transform"):
            ref = rpw.revit.uidoc.Selection.PickObject(ObjectType.Element, InPlaceFilter())
            selection = revit.doc.GetElement(ref)
            return selection
    except Exceptions.OperationCanceledException:
        forms.alert("Cancelled", ok=True, warn_icon=False, exitscript=True)


source_element = select_inplace_filter()

solids_dict = {}
curves = []
# get DB.GeometryElement
geo_element = source_element.get_Geometry(DB.Options())
bb = geo_element.GetBoundingBox()
family_origin = bb.Min

# iterate through DB.GeometryInstance and get all geometry, store it in a dictionary with Subcategory name
for instance_geo in geo_element:
    # get DB.GeometryElement
    geometry_element = instance_geo.GetInstanceGeometry()
    for geometry in geometry_element:
        # discard elements with 0 volume
        if isinstance(geometry, DB.Solid) and geometry.Volume >0:
            # translate in reference to geometry's bounding box corner. \
            # This prevents elements being copied too far from family origin.
            new_solid = DB.SolidUtils.CreateTransformed(geometry, inverted_transform_by_ref(bb.Min))
            solids_dict[new_solid] = get_subcat_name(geometry)
        # also collect curves
        elif isinstance(geometry, DB.Curve):
            new_curve = geometry.CreateTransformed(inverted_transform_by_ref(bb.Min))
            curves.append(new_curve)

el_cat_id = source_element.Category.Id.IntegerValue

templates_dict = {
    -2001000: "\Metric Casework.rft",
    -2000080: "\Metric Furniture.rft",
    -2001040: "\Metric Electrical Equipment.rft",
    -2001370: "\Metric Entourage.rft",
    -2001100: "\Metric Furniture System.rft",
    -2001120: "\Metric Lighting Fixture.rft",
    -2001140: "\Metric Mechanical Equipment.rft",
    -2001180: "\Metric Parking.rft",
    -2001360: "\Metric Planting.rft",
    -2001160: "\Metric Plumbing Fixture.rft",
    -2001260: "\Metric Site.rft",
    -2001350: "\Metric Specialty Equipment.rft",
}
template = None
if el_cat_id in templates_dict:
    template = templates_dict[el_cat_id]
else:
    template = "\Metric Generic Model.rft"
fam_template_path = __revit__.Application.FamilyTemplatePath + template



# define new family doc
try:
    new_family_doc = revit.doc.Application.NewFamilyDocument(fam_template_path)
except:
    forms.alert(msg="No Template",
                sub_msg="No Template for family found.",
                ok=True,
                warn_icon=True, exitscript=True)


# construct family and family type names:
project_number = revit.doc.ProjectInformation.Number
if not project_number:
    project_number = "000"
fam_name = project_number+ "_" + source_element.Symbol.Family.Name
# replace spaces (can cause errors)
fam_name = fam_name.strip(" ")

# if family under this name exists, keep adding Copy 1
if get_fam_by_name_and_cat(fam_name):
    while get_fam_by_name_and_cat(fam_name):
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
    # TODO: catch exception of name conflict
    except Exceptions.InvalidOperationException:
        forms.alert("Unable to Load Family", exitscript=True)


# Copy geometry from In-Place to Loadable family
with revit.Transaction(doc=new_family_doc, name="Copy Geometry"):
    parent_cat = new_family_doc.OwnerFamily.FamilyCategory
    is_instance_parameter = True # if the material is instance or type parameter
    new_mat_param = database.add_material_parameter(new_family_doc, "Material", is_instance_parameter)

    for geometry in solids_dict.keys():
        # create freeform element (copy of the geometry))
        copied_geo = DB.FreeFormElement.Create(new_family_doc, geometry)

        # assign material parameter
        try:
            geo_mat_param = copied_geo.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)
            new_family_doc.FamilyManager.AssociateElementParameterToFamilyParameter(geo_mat_param, new_mat_param)
        except Exception as err:
            logger.error(err)
        # if the geometry has a subcategory name
        if solids_dict[geometry]:
            # check if the subcategory exists
            check_if_exists = new_family_doc.Settings.Categories.Contains(solids_dict[geometry])
            # if yes, select subcategory by name
            if check_if_exists:
                subcat = [cat for cat in new_family_doc.Categories if cat.Name == solids_dict[geometry]]
            # if not create subcategory using parent category and string (name)
            else:
                subcat = new_family_doc.Settings.Categories.NewSubcategory(parent_cat, solids_dict[geometry])
            # assign subcategory
            copied_geo.Subcategory = subcat
    new_family_doc.Regenerate()

    for curve in curves:
        if isinstance(curve, DB.Line) and sk_plane(curve):
            p1 = curve.Evaluate(0, True)
            tangent = curve.ComputeDerivatives(0, True).BasisX
            rotate = tangent.CrossProduct(p1)
            plane = DB.Plane.CreateByNormalAndOrigin(rotate, p1)
            line_sk_plane = DB.SketchPlane.Create(new_family_doc, plane)
            new_curve = new_family_doc.FamilyCreate.NewModelCurve(curve, line_sk_plane)
        elif sk_plane(curve):
            new_curve = new_family_doc.FamilyCreate.NewModelCurve(curve, sk_plane(curve))
    new_family_doc.Regenerate()

# save and close family
save_opt = DB.SaveOptions()
new_family_doc.Save(save_opt)
new_family_doc.Close()


# non-structural type to place family instance
str_type = DB.Structure.StructuralType.NonStructural

# Reload family and place it in the same position as the original element
with DB.Transaction(revit.doc, "Reload Family") as t:
    t.Start()
    # TODO: solve error here
    loaded_f = revit.db.create.load_family(fam_path, doc=revit.doc)
    revit.doc.Regenerate()
    if not loaded_f:
        t.RollBack()
        forms.alert("Error loading family", exitscript=True)
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
    t.Commit()
print("Created and placed family instance : {1} {0} ".format(output.linkify(new_fam_instance.Id), fam_name))
