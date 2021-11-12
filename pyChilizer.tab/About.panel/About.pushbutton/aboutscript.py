# -*- coding: utf-8 -*-
#pylint: disable=E0401,E0602,W0703,W0613,C0103
import clr
import System

clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')

import sys, os
import webbrowser

from pyrevit import versionmgr
from pyrevit.versionmgr import urls
from pyrevit.versionmgr import about
from pyrevit import forms
from pyrevit import script
from pyrevit.userconfig import user_config
from pyrevit.framework import ComponentModel
from pyrevit.framework import ObservableCollection

import pyevent #pylint: disable=import-error


logger = script.get_logger()

# https://gui-at.blogspot.com/2009/11/inotifypropertychanged-in-ironpython.html
class reactive(property):
    """Decorator for WPF bound properties"""
    def __init__(self, getter):
        def newgetter(ui_control):
            try:
                return getter(ui_control)
            except AttributeError:
                return None
        super(reactive, self).__init__(newgetter)

    def setter(self, setter):
        def newsetter(ui_control, newvalue):
            oldvalue = self.fget(ui_control)
            if oldvalue != newvalue:
                setter(ui_control, newvalue)
                ui_control.OnPropertyChanged(setter.__name__)
        return property(
            fget=self.fget,
            fset=newsetter,
            fdel=self.fdel,
            doc=self.__doc__)


class Reactive(ComponentModel.INotifyPropertyChanged):
    """WPF property updator base mixin"""
    PropertyChanged, _propertyChangedCaller = pyevent.make_event()

    def add_PropertyChanged(self, value):
        self.PropertyChanged += value

    def remove_PropertyChanged(self, value):
        self.PropertyChanged -= value

    def OnPropertyChanged(self, prop_name):
        if self._propertyChangedCaller:
            args = ComponentModel.PropertyChangedEventArgs(prop_name)
            self._propertyChangedCaller(self, args)

class AboutWindow(forms.WPFWindow):

    img = None
    text = None

    @property
    def Img(self):
        return self.img

    @Img.setter
    def Img(self, value):
        self.img = value

    @property
    def Text(self):
        return self.text

    @Text.setter
    def Text(self, value):
        self.text = value
    
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        self.Text = "Just testing..."

        path = os.path.dirname(os.path.abspath(__file__))
        logo = os.path.join(path, 'logo.png')

        yellowbitmap = System.Windows.Media.Imaging.BitmapImage()
        yellowbitmap.BeginInit()
        yellowbitmap.UriSource = System.Uri(logo)
        yellowbitmap.DecodePixelHeight = 50        
 
        try:
            yellowbitmap.EndInit()       
            self.img = yellowbitmap   
            self.Img = yellowbitmap 
        except System.IO.FileNotFoundException as e:
            logger.error(e.Message)
        else:
            self.img = yellowbitmap

    def handle_url_click(self, sender, args): #pylint: disable=unused-argument
        """Callback for handling click on package website url"""
        return webbrowser.open_new_tab(sender.NavigateUri.AbsoluteUri)

    def handleclick(self, sender, args):
        self.Close()


AboutWindow('AboutWindow.xaml').show_dialog()
