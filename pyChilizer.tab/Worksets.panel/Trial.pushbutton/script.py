from pyrevit import script

import os

from pyrevit import extensions as exts
import pyrevit.extensions.extpackages as extpkgs

logger = script.get_logger()


"""Call the Reload command to refresh the UI and 
show up the newly installed package.
The command is currently hard-coded, could break in future
"""
def call_reload():
    from pyrevit.loader.sessionmgr import execute_command
    execute_command('pyrevitcore-pyrevit-pyrevit-tools-reload')


def install_ext_pkg(_pkg, _path):
    """Installs the selected extension
    """

    try:
        extpkgs.install(_pkg, _path)
        call_reload()
    except Exception as pkg_install_err:
        logger.error('Error installing package.'
                        ' | {}'.format(pkg_install_err))
        


"""Get the list of packages. Find Architype package and try to install it.
"""
packages = extpkgs.get_ext_packages()   
art_pkg = [pack for pack in packages if pack.name == 'ArchiPy'][0]

path = os.path.join(os.getenv('APPDATA'), "pyRevit", "Extensions")
# print(path)

if art_pkg and not art_pkg.is_installed:
    install_ext_pkg(art_pkg, path)
