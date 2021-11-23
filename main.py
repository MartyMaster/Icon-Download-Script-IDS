import urllib.request
from datetime import datetime, timedelta
import bz2
import os
import sys
import eccodes_get_nearest


#################################                   # Assumption: the latest model will give the most accurate forecast
#          Download             #
#################################


def download(lvl, var):
    try:
        url = build_url(lvl, var)
        urllib.request.urlretrieve(url, f"ICON_{var}.grib2.bz2")
    except:
        global oldermodel
        oldermodel = True
        url = build_url(lvl, var)
        urllib.request.urlretrieve(url, f"ICON_{var}.grib2.bz2")

    unzip_file(f"ICON_{var}.grib2.bz2")


def build_url(lvl, var):
    date = get_latest_model_date()
    hour = get_latest_model_hour()
    forecast_time = get_forecast_time()
    modellevel = lvl
    variable = var

    url = f"https://opendata.dwd.de/weather/nwp/icon-d2/grib/{hour}/{variable}" \
          f"/icon-d2_germany_regular-lat-lon_model-level_{date}{hour}_{forecast_time}_{modellevel}_{variable}.grib2.bz2"

    return url


def get_latest_model_date():
    model_date = round_down_time()[0]       # use only first return, which is rounded_time
    return model_date[0:8]                  # use only first 8 characters, ie the date


def get_latest_model_hour():
    model_hour = round_down_time()[0]        # use only first return, which is rounded_time
    return model_hour[9:11]                  # use only characters 9 and 10, ie the hour


def get_forecast_time():
    forecast_time = round_down_time()[1]      # use only second return, which is rounder
    return f"00{forecast_time}"               # add 00 in front to be in line with DWD nummeration


def round_down_time():                         # Takes current UTC and rounds down to a 3hour intervall, which is as current as possible but more than 2 hours ago. This is the update cycle of ICON-D2
    actual_time = datetime.utcnow()
    a = actual_time.hour

    if a == 0 or a == 3 or a == 6 or a == 9 or a == 12 or a == 15 or a == 18 or a == 21:
        rounder = 0
    elif a == 1 or a == 4 or a == 7 or a == 10 or a == 13 or a == 16 or a == 19 or a == 22:
        rounder = 1
    else:
        rounder = 2

    if oldermodel:
        rounder += 3

    rounded_time = str(actual_time.replace(microsecond=0, second=0, minute=0) - timedelta(hours=rounder))
    rounded_time = rounded_time.replace("-", "")
    rounded_time = rounded_time.replace(":", "")

    return rounded_time, rounder


#################################
#        Get Modellevel         #
#################################


def get_modellevel_from_altitude(lat, lon, alt):

    HHLs = []                                       # List of altitudes of all halflevels
    HFLs = []                                       # List of altitudes of all fulllevels

    for i in range(1, 67):                          # Get values for all halflevels
        HHL = read_value_from_gribfile(f"HHL_level_{i}.grib2", lat, lon)
        HHLs.append(HHL)

    for i in range(0, 65):                          # Calculate fulllevels from halflevels
        HFL = (HHLs[i] + HHLs[i+1])/2
        HFLs.append(HFL)

    level = min(range(len(HFLs)), key=lambda i: abs(HFLs[i] - alt)) + 1         # Returns the fulllevel which is closest to the given altitude

    return level


def download_HHL():                                 # This function should only be executed once at the beginning. The HHL_level files are stored locally and can be accessed anytime
    date = get_latest_model_date()
    hour = get_latest_model_hour()

    for i in range(1, 67):
        url = f"https://opendata.dwd.de/weather/nwp/icon-d2/grib/{hour}/hhl/icon-d2_germany_regular-lat-lon_time-invariant_{date}{hour}_000_{i}_hhl.grib2.bz2"
        print(url)
        urllib.request.urlretrieve(url, f"HHL_level_{i}.grib2.bz2")

        unzip_file(f"HHL_level_{i}.grib2.bz2")

    # for i in range(1, 67):
    #    os.remove(os.path.join(sys.path[0], f"HHL_level_{i}.grib2"))


#################################
#          Unzipping            #
#################################


def unzip_file(file):
    filepath = os.path.join(sys.path[0], file)

    comp_file = bz2.BZ2File(filepath)

    data = comp_file.read()                         # get the decompressed data
    newfilepath = filepath[:-4]                     # assuming the filepath ends with .bz2

    open(newfilepath, 'wb').write(data)             # write an uncompressed file

    os.remove(filepath)                             # remove the compressed file directly


#################################
#           Reading             #
#################################

def read_value_from_gribfile(file, lat, lon):

    value = eccodes_get_nearest.main(file, lat, lon)
    return value


#################################                  # not used
#         ICON Switcher         #
#################################

def icon_switcher(switcher):

    if switcher == "D2":
        return "icon-d2", "icon-d2_germany", 65
    elif switcher == "EU":
        return "icon-eu", "icon-eu_europe", 60


#################################
#             Main              #
#################################


def main():

    # ICON_switcher = "D2"        # Set to "EU" for ICON-EU model or "D2" for ICON-D2 model

    # download_HHL()                # This function should only be executed once at the beginning. The HHL_level files are stored locally and can be accessed anytime

    variables_of_interest = ["t", "p", "qv", "u", "v", "w"]

    points_in_space = ((47.45749472348071, 8.55596091912026, 500), (47.45749472348071, 8.55596091912026, 1000))

    for point in points_in_space:

        lat, lon, alt = point[0], point[1], point[2]

        lvl = get_modellevel_from_altitude(lat, lon, alt)

        print(point)

        for var in variables_of_interest:

            global oldermodel
            oldermodel = False
            download(lvl, var)

            value = read_value_from_gribfile(f"ICON_{var}.grib2", lat, lon)
            print(f"{var} = ", value)


if __name__ == '__main__':
    sys.exit(main())
