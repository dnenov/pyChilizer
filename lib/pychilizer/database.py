from pyrevit import revit, DB, script, forms, HOST_APP, coreutils
from pyrevit.revit.db import query



def get_sheet(some_number):
    sheet_nr_filter = query.get_biparam_stringequals_filter({DB.BuiltInParameter.SHEET_NUMBER: str(some_number)})
    found_sheet = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_Sheets) \
        .WherePasses(sheet_nr_filter) \
        .WhereElementIsNotElementType().ToElements()

    return found_sheet


def get_view(some_name):
    view_name_filter = query.get_biparam_stringequals_filter({DB.BuiltInParameter.VIEW_NAME: some_name})
    found_view = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_Views) \
        .WherePasses(view_name_filter) \
        .WhereElementIsNotElementType().ToElements()

    return found_view


def get_fam(some_name):
    fam_name_filter = query.get_biparam_stringequals_filter({DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM: some_name})
    found_fam = DB.FilteredElementCollector(revit.doc) \
        .OfCategory(DB.BuiltInCategory.OST_GenericModel) \
        .WherePasses(fam_name_filter) \
        .WhereElementIsNotElementType().ToElements()

    return found_fam


def param_set_by_cat(cat):
    # get all project type parameters of a given category
    # can be used to gather parameters for UI selection
    all_gm = DB.FilteredElementCollector(revit.doc).OfCategory(cat).WhereElementIsElementType().ToElements()
    parameter_set = []
    for gm in all_gm:
        params = gm.Parameters
        for p in params:
            if p not in parameter_set and p.IsReadOnly == False:
                parameter_set.append(p)
    return parameter_set



def create_sheet(sheet_num, sheet_name, titleblock):
    sheet_num = str(sheet_num)

    new_datasheet = DB.ViewSheet.Create(revit.doc, titleblock)
    new_datasheet.Name = sheet_name

    while get_sheet(sheet_num):
        sheet_num = coreutils.increment_str(sheet_num, 1)
    new_datasheet.SheetNumber = str(sheet_num)

    return new_datasheet


def set_anno_crop(v):
    anno_crop = v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
    anno_crop.Set(1)
    return anno_crop


def apply_vt(v, vt):
    if vt:
        v.ViewTemplateId = vt.Id
    return


def get_name(el):
    return DB.Element.Name.__get__(el)


def create_parallel_bbox(line, crop_elem, offset=300/304.8):
    # create section parallel to x (solution by Building Coder)
    p = line.GetEndPoint(0)
    q = line.GetEndPoint(1)
    v = q - p

    # section box width
    w = v.GetLength()
    bb = crop_elem.get_BoundingBox(None)
    minZ = bb.Min.Z
    maxZ = bb.Max.Z
    # height = maxZ - minZ

    min = DB.XYZ(-w, minZ - offset, -offset)
    max = DB.XYZ(w, maxZ + offset, offset)

    centerpoint = p + 0.5 * v
    direction = v.Normalize()
    up = DB.XYZ.BasisZ
    view_direction = direction.CrossProduct(up)

    t = DB.Transform.Identity
    t.Origin = centerpoint
    t.BasisX = direction
    t.BasisY = up
    t.BasisZ = view_direction

    section_box = DB.BoundingBoxXYZ()
    section_box.Transform = t
    section_box.Min = min
    section_box.Max = max

    pt = DB.XYZ(centerpoint.X, centerpoint.Y, minZ)
    point_in_front = pt+(-3)*view_direction
    #TODO: check other usage
    return section_box


def char_series(nr):
    from string import ascii_uppercase
    series = []
    for i in range(0,nr):
        series.append(ascii_uppercase[i])
    return series


def char_i(i):
    from string import ascii_uppercase
    return ascii_uppercase[i]


def get_view_family_types(viewtype, doc=revit.doc):
    return [vt for vt in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType) if
                vt.ViewFamily == viewtype]


def get_generic_template_path():
    fam_template_path = __revit__.Application.FamilyTemplatePath + "\Metric Generic Model.rft"
    from os.path import isfile
    if isfile(fam_template_path):
        return fam_template_path
    else:
        forms.alert(title="No Generic Template Found", msg="There is no Generic Model Template in the default location. Can you point where to get it?", ok=True)
        fam_template_path = forms.pick_file(file_ext="rft", init_dir="C:\ProgramData\Autodesk\RVT "+HOST_APP.version+"\Family Templates")
        return fam_template_path

# def remember_config():
