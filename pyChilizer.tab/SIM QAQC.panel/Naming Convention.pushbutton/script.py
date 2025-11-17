import sys

from pyrevit import DB, UI, revit, HOST_APP
from pyrevit import script, forms, coreutils
import xlrd

doc = revit.doc
FEC = DB.FilteredElementCollector
BIC = DB.BuiltInCategory

import re

output = script.get_output()
worksets = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset).ToWorksets()

disciplines = ["Ar", "St", "Me", "El", "Ir", "Fa", "Pl", "La"]
categories = ["AVD",
              "ATe",
              "Cas",
              "Cei",
              "CDe",
              "CFi",
              "CNd",
              "CTr",
              "CTf",
              "Col",
              "CWP",
              "Cwp",
              "CWS",
              "CWM",
              "Ano",
              "DAc",
              "DDe",
              "DFi",
              "DSy",
              "Dor",
              "EEq",
              "EEx",
              "Ent",
              "FPr",
              "IFS",
              "EFS",
              "IFF",
              "Fur",
              "FAd",
              "FSy",
              "Har",
              "LFx",
              "LDe",
              "Mas",
              "MEq",
              "Par",
              "PAc",
              "Pla",
              "PFx",
              "PSy",
              "PTy",
              "Bal",
              "Ram",
              "Roa",
              "Rai",
              "Rof",
              "SEq",
              "SDe",
              "SPr",
              "Sig",
              "Sit",
              "Sta",
              "SCo",
              "SFr",
              "SFo",
              "Top",
              "Vtr",
              "EWS",
              "IWS",
              "IWF",
              "Win",
              "Joi",
              "DTi",
              "EMa",
              "GMo",
              "PFi",
              "PEq",
              "Flo",
              "Dpa",
              ]

system_fam_category_ids = [
    DB.ElementId(BIC.OST_Walls).IntegerValue,
    DB.ElementId(BIC.OST_Floors).IntegerValue,
    DB.ElementId(BIC.OST_Stairs).IntegerValue,
    DB.ElementId(BIC.OST_Ramps).IntegerValue,
    DB.ElementId(BIC.OST_Railings).IntegerValue,
    DB.ElementId(BIC.OST_Ceilings).IntegerValue,
    DB.ElementId(BIC.OST_Roofs).IntegerValue,
]

system_fam_categories = [
    BIC.OST_Walls,
    BIC.OST_Floors,
    BIC.OST_Stairs,
    BIC.OST_Ramps,
    BIC.OST_Railings,
    BIC.OST_Ceilings,
    BIC.OST_Roofs,
]


def get_all_model_families():
    all_elements = FEC(doc).OfClass(DB.FamilyInstance).ToElements()
    for lc in system_fam_categories:
        els_of_system_category = FEC(doc).OfCategory(lc).WhereElementIsNotElementType().ToElements()
        for el in els_of_system_category:
            all_elements.Add(el)
    not_placeholders = []
    for i in all_elements:
        workset_id = i.WorksetId
        for w in worksets:
            if w.Id == workset_id:
                if "XX" not in str(w.Name) and "Enscape" not in str(w.Name) and "AA_Site Context" not in str(w.Name):
                    not_placeholders.append(i)

    families = set()
    for inst in not_placeholders:
        try:
            category = inst.Category
            if category and category.CategoryType == DB.CategoryType.Model:
                if category.Id.IntegerValue in system_fam_category_ids:
                    families.add(inst.get_Parameter(DB.BuiltInParameter.ELEM_TYPE_PARAM).AsValueString())
                else:
                    fam = inst.Symbol.Family
                    if fam:
                        families.add(fam.Name)
        except Exception as e:
            print("Error processing instance: {}".format(e))
    return families


wrong_name = {"Wrong Pattern": [], "Wrong Originator": [], "Wrong Discipline": [], "Wrong Category": []}
correct_names = []
pattern = r"^([AZO])([A-Za-z]{2})\-([A-Za-z]{3})_(.+)$"
all_families = get_all_model_families()
output.print_md("#TOTAL FAMILIES : _{}_".format(len(all_families)))

for family_name in all_families:
    match = re.match(pattern, family_name)
    if not match:
        wrong_name["Wrong Pattern"].append(family_name)
        continue
    try:
        a, bb, ccc, rest = match.groups()
    except AttributeError:
        continue
    if a not in ["A", "Z", "O"]:
        wrong_name["Wrong Originator"].append(family_name)
    if bb not in disciplines:
        wrong_name["Wrong Discipline"].append(family_name)
    if ccc not in categories:
        wrong_name["Wrong Category"].append(family_name)

labels = {
    "Wrong Pattern": "_Pattern_",
    "Wrong Originator": "_Originator_",
    "Wrong Discipline": "_Discipline_",
    "Wrong Category": "_Category_"
}
for key, label in labels.items():
    if wrong_name.get(key):
        output.print_md("##{}".format(label))
        wrong_score = 100 - round(float(len(wrong_name[key])) / len(all_families) * 100, 2)
        output.print_md("###Correct: {}%".format(wrong_score))
        output.print_md("*{} wrong values:*".format(len(wrong_name[key]), len(all_families)))
        for item in wrong_name[key]:
            print(item)
