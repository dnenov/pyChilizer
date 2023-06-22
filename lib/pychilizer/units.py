from pyrevit import revit, DB, script, forms, HOST_APP, coreutils


def convert_length_to_internal(value, doc=revit.doc):
    # convert length units from display units to internal
    display_units = get_length_units(doc)
    converted = DB.UnitUtils.ConvertToInternalUnits(value, display_units)
    return converted

def convert_length_to_display(value, doc=revit.doc):
    # convert length units from internal to display
    display_value = DB.UnitUtils.ConvertFromInternalUnits(value, get_length_units(doc))
    return display_value

def get_length_units(doc):
    # fetch Revit's internal units depending on the Revit version
    units = doc.GetUnits()

    # print ("Doc name {}".format(doc.Title))

    if HOST_APP.is_newer_than(2021):
        int_length_units = units.GetFormatOptions(DB.SpecTypeId.Length).GetUnitTypeId()
    else:
        int_length_units = units.GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
    return int_length_units


def get_length_units_name(doc):
    units = get_length_units(doc)
    if 'millimetres' in units.TypeId:
        return 'mm'
    elif 'feet' in units.TypeId:
        return "ft"
    else:
        return ""

def degree_conv(x):
    import math
    return (x * 180) / math.pi


def is_metric(doc):
    # check if doc is metric
    if doc.DisplayUnitSystem == DB.DisplayUnit.METRIC:
        # print ("IS METRIC")
        return True
    else:
        # print ("IMPERIAL")
        return False


def correct_input_units(val, doc):
    import re
    try:
        digits = float(val)
    except ValueError:
        # format the string using regex
        digits = re.findall("[0-9.]+", val)[0]
    # get internal units for
    # display_units = get_length_units(doc)
    res = convert_length_to_internal(float(digits), doc)
    # print ("convert from display units: {} \n from float {}\n result {}".format(display_units, digits, res))

    return res


