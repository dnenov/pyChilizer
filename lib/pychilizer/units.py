from pyrevit import revit, DB, script, forms, HOST_APP, coreutils


def convert_length_to_internal(d_units):
    # convert length units from display units to internal
    internal_units = get_int_length_units()
    converted = DB.UnitUtils.ConvertToInternalUnits(d_units, internal_units)
    return converted


def get_int_length_units(doc=revit.doc):
    # fetch Revit's internal units depending on the Revit version
    units = doc.GetUnits()
    if HOST_APP.is_newer_than(2021):
        int_length_units = units.GetFormatOptions(DB.SpecTypeId.Length).GetUnitTypeId()
    else:
        int_length_units = units.GetFormatOptions(DB.UnitType.UT_Length).DisplayUnits
    return int_length_units


def degree_conv(x):
    import math
    return (x * 180) / math.pi


def is_metric(doc=revit.doc):
    # check if doc is metric
    if doc.DisplayUnitSystem == DB.DisplayUnit.METRIC:
        return True
    else:
        return False


def correct_input_units(val):
    import re
    try:
        digits = float(val)
    except ValueError:
        # format the string using regex
        digits = re.findall("[0-9.]+", val)[0]
    # get internal units for conversion
    int_units = get_int_length_units()
    return DB.UnitUtils.ConvertToInternalUnits(float(digits), int_units)


