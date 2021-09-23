# 09/14/2021 Version

# dependencies
import clr

clr.AddReference('System.Windows.Forms')
clr.AddReference('IronPython.Wpf')

# Importing external libraries
clr.AddReference("RevitNodes")
import Revit

clr.ImportExtensions(Revit.Elements)
clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager

clr.AddReference("RevitAPI")
import Autodesk
from Autodesk.Revit.DB import *
import System
from System.Collections.Generic import *

import re
from collections import namedtuple
from pyrevit import forms
from pyrevit import revit, DB

# Defining our current Revit document as 'doc'
uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

__doc__ = 'Manage worksets and pinning of critical elements and links.' \
 \
    # find the path of ui.xaml

from pyrevit import UI
from pyrevit import script

xamlfile = script.get_bundle_file('ui.xaml')

# import WPF creator and base Window
import wpf
from System import Windows

class CadLinkItem:
    def __init__(self, name):
        self.name = name


class MCEWindow(Windows.Window):
    def __init__(self):
        wpf.LoadComponent(self, xamlfile)
        self.workset_levels_cb.ItemsSource = self._get_worksets_list()
        self.workset_grids_cb.ItemsSource = self._get_worksets_list()
        self.workset_rooms_cb.ItemsSource = self._get_worksets_list()
        self.workset_roomboundaries_cb.ItemsSource = self._get_worksets_list()
        self.workset_areas_cb.ItemsSource = self._get_worksets_list()
        self.workset_areaboundaries_cb.ItemsSource = self._get_worksets_list()
        self.workset_property_cb.ItemsSource = self._get_worksets_list()
        self.workset_scopebox_cb.ItemsSource = self._get_worksets_list()
        self.workset_ref_cb.ItemsSource = self._get_worksets_list()
        self.rvtlinks_dg.ItemsSource = self._get_rvtlinks_list()
        self.cadlinks_dg.ItemsSource = self._get_cadlinks_list()

    @forms.reactive
    def rvtlinkname(self):
        return self._rvtlinkname

    @rvtlinkname.setter
    def rvtlinkname(self, value):
        self._rvtlinkname = value

    # get worksets dropdown
    def _setup_worksets_list(self):
        print("Changing workset")
        # self.workset_levels_cb.ItemsSource = self._get_worksets_list()
        self.workset_levels_cb.SelectedIndex = 0
        if self.workset_levels_cb.ItemsSource:
            self.enable_element(self.workset_levels_cb)
        else:
            self.disable_element(self.workset_levels_cb)

    def _get_worksets_list(self):
        worksets_collector = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset)
        worksets_list = []
        for workset in worksets_collector:
            worksets_list.append(workset.Name)
        print(worksets_list)
        return worksets_list

    # set/get rvtlink names list:
    def _setup_rvtlinks_list(self):
        # self.rvtlinks_dg.ItemsSource = self._get_rvtlinks_list()
        self.rvtlinks_dg.SelectedIndex = 0
        if self.rvtlinks_dg.ItemsSource:
            self.enable_element(self.rvtlinks_dg)
        else:
            self.disable_element(self.rvtlinks_dg)

    def _get_rvtlinks_list(self):
        rvtlinks_collector = DB.FilteredElementCollector(doc) \
            .OfCategory(DB.BuiltInCategory.OST_RvtLinks) \
            .WhereElementIsNotElementType()
        rvtlinks_list = []
        for rvtlink in rvtlinks_collector:
            rvtlinks_list.append(rvtlink.Name)
        return rvtlinks_list

    # set/get cadlink names list:
    def _setup_cadlinks_list(self):
        self.cadlinks_dg.SelectedIndex = 0
        if self.cadlinks_dg.ItemsSource:
            self.enable_element(self.cadlinks_dg)
        else:
            self.disable_element(self.cadlinks_dg)

    def _get_cadlinks_list(self):
        cadlinks_collector = DB.FilteredElementCollector(doc) \
            .OfClass(DB.ImportInstance) \
            .WhereElementIsNotElementType().ToElements()
        cadlinks_list = []
        for cadlink in cadlinks_collector:
            cadlinks_list.append(CadLinkItem(cadlink.Category.Name))
        print(cadlinks_list)
        return cadlinks_list

    # event handlers

    # def _setup_worksets_list(self, sender, args):
    # UI.NewValue()
    # tblocks = revit.query.get_elements_by_categories(
    #    [DB.BuiltInCategory.OST_TitleBlocks],

    # get rvtlinks list
    # def _rvtlinks_list(self, value):
    # self.rvtlinks_dg.ItemsSource = value


# let's show the window (model)
MCEWindow().ShowDialog()