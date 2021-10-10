__title__ = "Populate COBie\nInformation"
__doc__ = "Populate COBie related information inside Families."

from pyrevit import HOST_APP
from pyrevit import revit, DB, script, forms

uidoc = revit.uidoc
doc = revit.doc

df = HOST_APP.app.OpenSharedParameterFile()
dgs = df.Groups

s_params = {}
debug = ''

for dg in dgs:
    for d in dg.Definitions:
        if d:
            s_param[ed.Name] = ed
            debug += f'Parameter {ed.Name}\n'

