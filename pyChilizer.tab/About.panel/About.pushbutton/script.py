# dependencies
import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('IronPython.Wpf')

import sys, os
import webbrowser

#Importing external libraries
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

#Defining our current Revit document as 'doc'
uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

__doc__ = 'pyChilizer toolbar'\
          
# find the path of ui.xaml
from pyrevit import UI
from pyrevit import script


logger = script.get_logger()
xamlfile = script.get_bundle_file('AboutWindow.xaml')

# import WPF creator and base Window
import wpf
from System import Windows

class AboutWindow(Windows.Window):
    def __init__(self):
        wpf.LoadComponent(self, xamlfile)
        # self.logo_img.Source = self._get_logo_image()
 
    #get logo png from root folder
    def _get_logo_image(self):
        print("test")
        return
        path = os.path.dirname(os.path.abspath(__file__))
        logo = os.path.join(path, 'logo.png')

        yellowbitmap = System.Windows.Media.Imaging.BitmapImage()
        yellowbitmap.BeginInit()
        yellowbitmap.UriSource = System.Uri(logo)

        try:
            yellowbitmap.EndInit()       
            return yellowbitmap   
        except System.IO.FileNotFoundException as e:
            logger.error(e.Message)
        else:
            return yellowbitmap

    def handle_url_click(self, sender, args): #pylint: disable=unused-argument
        """Callback for handling click on package website url"""
        return webbrowser.open_new_tab(sender.NavigateUri.AbsoluteUri)

    def handleclick(self, sender, args):
        self.Close()

    
#let's show the window (model)
AboutWindow().ShowDialog()




