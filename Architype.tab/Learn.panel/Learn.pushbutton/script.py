__title__ = "Architype\nLearn"
__doc__ = "Architype Learn \nv1.0"

from pyrevit import revit, DB, HOST_APP
from pyrevit.framework import List
from pyrevit.forms import ProgressBar

from System import EventHandler, Uri
from Autodesk.Revit.UI.Events import ViewActivatedEventArgs, ViewActivatingEventArgs
from Autodesk.Revit.UI import DockablePaneId
from Autodesk.Revit import UI
from System import Guid
from pyrevit import HOST_APP

app = HOST_APP.uiapp

dpid = DockablePaneId(Guid("39FA492A-6F72-465C-83C9-F7662B89F62C"))
dp = app.GetDockablePane(dpid)

if dp.IsShown():
    dp.Hide()
else:
    dp.Show()