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

# Category Ban List
cat_ban_list = [
    -2000260,   # dimensions
    -2000261,   # Automatic Sketch Dimensions
    -2000954,   # railing path extension lines
    -2000045,   # <Sketch>
    -2000067,   # <Stair/Ramp Sketch: Boundary>
    -2000262,   # Constraints
    -2000920,   # Landings
    -2000919,   # Stair runs
    -2000123,   # Supports
    -2000173,   # curtain wall grids
    -2000171,   # curtain wall mullions
    -2000530,   # reference places
    -2000127,   # Balusters
    -2000947,   # Handrail
    -2000946,   # Top Rail
    -2002000,    # Detail Items
    -2000150,    # Generic Annotations
    -2001260,    # Site
    -2000280,    # Title Blocks
    # -2000170,   # curtain panels
]

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
        if p.StorageType == DB.StorageType.String and \
         p.Definition.ParameterType == DB.ParameterType.Text and \
         not p.IsReadOnly]

    return parameters

family_instances = DB.FilteredElementCollector(doc).OfClass(DB.FamilyInstance).ToElements() # get all family instance categories

cat_dict1 = {c.Name: c for c in [fam.Category for fam in family_instances] if c.Id.IntegerValue not in cat_ban_list} # {key: value for value in list}
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

cat_name = ''

try:    
    # assign chosen parameters  
    cat_name = form.values["cat_combobox"].Name
except:
    forms.alert_ifnot(cat_name, "No selection", exitscript=True)


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

parameter = None
prefix = None
leading = None

try:    
    parameter = form.values["param_combobox"]
    prefix = form.values["prefix_box"]
    leading = int(form.values["leading_box"])
except:
    forms.alert("Bad selection")
    script.exit()

if not parameter or not prefix or not leading:
    forms.alert("Bad selection")
    script.exit()

if not leading:
    forms.alert("Incorrect leading number")
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