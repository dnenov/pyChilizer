# -*- coding: utf-8 -*-

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


def get_fam_types(family_name):
    fam_bip_id = DB.ElementId(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM)
    fam_bip_provider = DB.ParameterValueProvider(fam_bip_id)
    fam_filter_rule = DB.FilterStringRule(fam_bip_provider, DB.FilterStringEquals(), family_name, True)
    fam_filter = DB.ElementParameterFilter(fam_filter_rule)

    collector = DB.FilteredElementCollector(revit.doc) \
        .WherePasses(fam_filter) \
        .WhereElementIsElementType()

    return collector


def get_fam_any_type(family_name):
    fam_bip_id = DB.ElementId(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM)
    fam_bip_provider = DB.ParameterValueProvider(fam_bip_id)
    fam_filter_rule = DB.FilterStringRule(fam_bip_provider, DB.FilterStringEquals(), family_name, True)
    fam_filter = DB.ElementParameterFilter(fam_filter_rule)

    collector = DB.FilteredElementCollector(revit.doc) \
        .WherePasses(fam_filter) \
        .WhereElementIsElementType() \
        .FirstElement()

    return collector



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


def get_view_family_types(viewtype, doc):
    return [vt for vt in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType) if
                vt.ViewFamily == viewtype]


def get_generic_template_path():
    fam_template_folder = __revit__.Application.FamilyTemplatePath

    ENG = "\Metric Generic Model.rft"
    FRA = "\Modèle générique métrique.rft"
    GER = "\Allgemeines Modell.rft"
    ESP = "\Modelo genérico métrico.rft"
    RUS = "\Метрическая система, типовая модель.rft"

    if ("French") in fam_template_folder:
        generic_temp_name = FRA
    elif ("Spanish") in fam_template_folder:
        generic_temp_name = ESP
    elif ("German") in fam_template_folder:
        generic_temp_name = GER
    elif ("Russian") in fam_template_folder:
        generic_temp_name = RUS
    else:
        generic_temp_name = ENG

    gen_template_path = fam_template_folder + generic_temp_name
    from os.path import isfile
    if isfile(gen_template_path):
        return gen_template_path
    else:
        forms.alert(title="No Generic Template Found", msg="There is no Generic Model Template in the default location. Can you point where to get it?", ok=True)
        fam_template_path = forms.pick_file(file_ext="rft", init_dir="C:\ProgramData\Autodesk\RVT "+HOST_APP.version+"\Family Templates")
        return fam_template_path


def get_mass_template_path():
    fam_template_folder = __revit__.Application.FamilyTemplatePath

    ENG = "\Conceptual Mass\Metric Mass.rft"
    FRA = "\Volume conceptuel\Volume métrique.rft"
    GER = "\Entwurfskörper\Entwurfskörper.rft"
    ESP = "\Masas conceptuales\Masa métrica.rft"
    RUS = "\Концептуальные формы\Метрическая система, формообразующий элемент.rft"

    if ("French") in fam_template_folder:
        mass_temp_name = FRA
    elif ("Spanish") in fam_template_folder:
        mass_temp_name = ESP
    elif ("German") in fam_template_folder:
        mass_temp_name = GER
    elif ("Russian") in fam_template_folder:
        mass_temp_name = RUS
    else:
        mass_temp_name = ENG

    mass_template_path = fam_template_folder + mass_temp_name
    from os.path import isfile
    if isfile(mass_template_path):
        return mass_template_path
    else:
        forms.alert(title="No Mass Template Found", msg="There is no Mass Model Template in the default location. Can you point where to get it?", ok=True)
        fam_template_path = forms.pick_file(file_ext="rft", init_dir="C:\ProgramData\Autodesk\RVT "+HOST_APP.version+"\Family Templates")
        return fam_template_path


def vt_name_match(vt_name, doc):
    # return a view template with a given name, None if not found
    views = DB.FilteredElementCollector(doc).OfClass(DB.View)
    vt_match = None
    for v in views:
        if v.IsTemplate and v.Name == vt_name:
            vt_match = v.Name
    return vt_match

    
def vp_name_match(vp_name, doc):
    # return a view template with a given name, None if not found
    views = DB.FilteredElementCollector(doc).OfClass(DB.Viewport)
    for v in views:
        if v.Name == vp_name:
            return v.Name            
    return views.FirstElement().Name


def tb_name_match(tb_name, doc):
    titleblocks = DB.FilteredElementCollector(doc).OfCategory(
        DB.BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType()
    tb_match = None
    for tb in titleblocks:
        if revit.query.get_name(tb) == tb_name:
            tb_match = revit.query.get_name(tb)
    return tb_match

def unique_view_name(name, suffix=None):
    unique_v_name = name + suffix
    while get_view(unique_v_name):
        unique_v_name = unique_v_name + " Copy 1"
    return unique_v_name


def shift_list(l, n):
    return l[n:] + l[:n]


def get_viewport_types(doc=revit.doc):
    # get viewport types using a parameter filter
    bip_id = DB.ElementId(DB.BuiltInParameter.VIEWPORT_ATTR_SHOW_LABEL)
    bip_provider = DB.ParameterValueProvider(bip_id)
    rule = DB.FilterIntegerRule(bip_provider, DB.FilterNumericGreaterOrEqual(), 0)
    param_filter = DB.ElementParameterFilter(rule)

    collector = DB.FilteredElementCollector(doc) \
        .WherePasses(param_filter) \
        .WhereElementIsElementType()\
        .ToElements()

    return collector


def get_vp_by_name(name, doc=revit.doc):
    #
    bip_id = DB.ElementId(DB.BuiltInParameter.VIEWPORT_ATTR_SHOW_LABEL)
    bip_provider = DB.ParameterValueProvider(bip_id)
    rule = DB.FilterIntegerRule(bip_provider, DB.FilterNumericGreaterOrEqual(), 0)
    param_filter = DB.ElementParameterFilter(rule)

    type_bip_id = DB.ElementId(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
    type_bip_provider = DB.ParameterValueProvider(type_bip_id)
    type_filter_rule = DB.FilterStringRule(type_bip_provider, DB.FilterStringEquals(), name, True)
    type_filter = DB.ElementParameterFilter(type_filter_rule)

    and_filter = DB.LogicalAndFilter(param_filter, type_filter)



    collector = DB.FilteredElementCollector(doc) \
        .WherePasses(and_filter) \
        .WhereElementIsElementType()\
        .FirstElement()

    return collector