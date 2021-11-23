import System

from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Architecture import *
from Autodesk.Revit.DB.Analysis import *
from Autodesk.Revit.UI import *
from Autodesk.Revit.UI.Selection import *

from pyrevit import revit, DB, UI
from pyrevit import forms, script

from rpw.ui.forms import (FlexForm, Label, ComboBox, Separator, Button, TextBox)

#set the active Revit application and document
app = __revit__.Application
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
active_view = doc.ActiveView

# Selection Filter
class CustomISelectionFilter(ISelectionFilter):
    def __init__(self, cat):
        self.cat = cat

    def AllowElement(self, e):
        if e.Category.Id.IntegerValue == int(self.cat):
            return True
        else:
            return False

    @staticmethod
    def AllowReference(ref, point):
        return True

def GetBICFromCat(_cat):
    # Convert categoryId to BuiltInCategory https://git.io/J1d6O @Gui Talarico    
    bic = System.Enum.ToObject(DB.BuiltInCategory, _cat.Id.IntegerValue)  
    return bic

def GetInstanceParameters(_cat):  
    el = DB.FilteredElementCollector(doc) \
    .WhereElementIsNotElementType() \
    .OfCategory(_cat) \
    .ToElements() 

    if not el:
        forms.alert("No elements of this category found in the project.")
        script.exit()

    parameters = [p.Definition.Name for p in el[0].Parameters \
        if p.StorageType == DB.StorageType.String and p.Definition.ParameterType == DB.ParameterType.Text]

    return parameters

family_instances = DB.FilteredElementCollector(doc).OfClass(DB.FamilyInstance).ToElements() # get all family instance categories
cat_dict1 = {c.Name: c for c in [fam.Category for fam in family_instances]} # {key: value for value in list}
cat_rooms = DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_Rooms)
cat_dict1[cat_rooms.Name] = cat_rooms   # Add Rooms to the list of Categories

# construct rwp UI for Category
components = [
    Label("Pick Category:"),
    ComboBox(name="cat_combobox", options=cat_dict1, sorted=True),
    Button("Select")
]
form = FlexForm("Select", components)
form.show()

# assign chosen parameters
cat_name = form.values["cat_combobox"].Name
cat = GetBICFromCat(form.values["cat_combobox"])    #BuiltInCategory
param_dict1 = GetInstanceParameters(cat)

# construct rwp UI for Parameter and Prefix
components = [
    Label("Pick Parameter:"),
    ComboBox(name="param_combobox", options=param_dict1, sorted=True),
    Label("Prefix"),
    TextBox(name="prefix_box", Text="X00_"),
    Label("Leading zeroes"),
    TextBox(name="leading_box", Text="3"),
    Button("Select")
]
form = FlexForm("Select", components)
form.show()

parameter = form.values["param_combobox"]
prefix = form.values["prefix_box"]
leading = int(form.values["leading_box"])

if not leading:
    form.alert("Incorrect leading number")
    leading = 3

spline = doc.GetElement(uidoc.Selection.PickObject(UI.Selection.ObjectType.Element, \
    CustomISelectionFilter(DB.BuiltInCategory.OST_Lines), \
        "Select Spline"))

elements = uidoc.Selection.PickElementsByRectangle(CustomISelectionFilter(cat), \
        "Select Elements")


# The dictionary containing all keys=elements + values=location
door_dict = {}
sorted_door_dict = {}
parameters = []

for e in elements:
    el = doc.GetElement(e.Id)
    loc = el.Location
    if loc:
        door_dict[el] = loc.Point
    else:
        door_dict[el] = el.get_BoundingBox(doc.ActiveView).Min

for dr, pt in door_dict.items():
    crv = spline.GeometryCurve
    param = crv.ComputeNormalizedParameter(crv.Project(pt).Parameter)
    sorted_door_dict[dr] = param
    parameters.append(param)

sorted = sorted(sorted_door_dict, key=sorted_door_dict.get)

counter = 1

with revit.Transaction("Renumber Elements", doc):
    for el in sorted:
        el.LookupParameter(parameter).Set(str(prefix + str(counter).zfill(leading)))
        counter += 1

forms.alert("{0} {1} renumbered.".format(len(sorted), cat_name))