import System.IO
import enum

from pyrevit import forms

files = 0
lengths = 0

def GetDirectories(_path, _search_pat = "*", _search_opt = System.IO.SearchOption.TopDirectoryOnly):
    if _search_opt is System.IO.SearchOption.TopDirectoryOnly:
        return System.IO.Directory.GetDirectories(_path, _search_pat)

    directories = GetDirectories(_path, _search_pat)

    for dir in directories:
        directories.extend(GetDirectories((dir, _search_pat)))

    return directories


# Recursively, go into each sub-folder
def DeleteRecursive(_dir):
    dir_info = System.IO.DirectoryInfo(_dir)
    # print(dir_info.FullName)
    directories = GetDirectories(dir_info.FullName)
    # print(directories)

    for dir in directories:
        DeleteRecursive(dir)

    global files
    global lengths

    for file in dir_info.EnumerateFiles("*.0???.*"):
        lengths += file.Length
        files += 1
        file.Delete()



# Enum for size units
class SIZE_UNIT(enum.Enum):
   BYTES = 1
   KB = 2
   MB = 3
   GB = 4


def convert_unit(size_in_bytes, unit):
   """ Convert the size from bytes to other units like KB, MB or GB"""
   if unit == SIZE_UNIT.KB:
       return size_in_bytes/1024
   elif unit == SIZE_UNIT.MB:
       return size_in_bytes/(1024*1024)
   elif unit == SIZE_UNIT.GB:
       return size_in_bytes/(1024*1024*1024)
   else:
       return size_in_bytes


# Delete all files in the folder and all sub-folders
def Delete():
    global files
    global lengths

    directory = forms.pick_folder("Select parent folder of backup families or files to be purged")

    if directory:
        DeleteRecursive(directory)

    b = convert_unit(lengths, SIZE_UNIT.MB)

    print(str(files) + ' files with a total of ' + str(b) + ' MB deleted.')



Delete()

print("done")
