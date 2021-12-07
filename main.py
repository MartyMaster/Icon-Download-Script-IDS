import urllib.request
from datetime import datetime, timedelta
import time
import bz2
import os
import sys
import eccodes_get_nearest
from eccodes import *
import fnmatch


#################################
#          Download             #
#################################


def download(lvl, var, time_at_point):
    try:
        url, filename = build_url(lvl, var, time_at_point)
        urllib.request.urlretrieve(url, filename)
    except:
        global oldermodel
        oldermodel = True

        url, filename = build_url(lvl, var, time_at_point)
        urllib.request.urlretrieve(url, filename)

    unzip_file(filename)


def build_url(lvl, var, time_at_point):
    rounded_time = round_down_time(time_at_point)

    date = rounded_time[0][0:8]
    hour = rounded_time[0][9:11]
    forecast_time = str(rounded_time[1]).zfill(3)                       # fill with 0 until string is 3 digits long

    modellevel = lvl
    variable = var

    if ICON_switcher == "D2":
        filename = f"icon-d2_germany_regular-lat-lon_model-level_{date}{hour}_{forecast_time}_{modellevel}_{variable}.grib2.bz2"
        url = f"https://opendata.dwd.de/weather/nwp/icon-d2/grib/{hour}/{variable}/{filename}"
    elif ICON_switcher == "EU":
        filename = f"icon-eu_europe_regular-lat-lon_model-level_{date}{hour}_{forecast_time}_{modellevel}_{variable.upper()}.grib2.bz2"
        url = f"https://opendata.dwd.de/weather/nwp/icon-eu/grib/{hour}/{variable}/{filename}"

    return url, filename


def round_down_time(time_at_point):                         # takes current UTC and rounds down to a 3hour interval. This is the update cycle of ICON-D2
    actual_time = datetime.utcnow()
    a = actual_time.hour

    if a == 0 or a == 3 or a == 6 or a == 9 or a == 12 or a == 15 or a == 18 or a == 21:
        rounder = 0
    elif a == 1 or a == 4 or a == 7 or a == 10 or a == 13 or a == 16 or a == 19 or a == 22:
        rounder = 1
    else:
        rounder = 2

    if oldermodel:                                          # if latest model is not yet available take the one from 3 hours before
        rounder += 3

    rounded_time = actual_time.replace(microsecond=0, second=0, minute=0) - timedelta(hours=rounder)

    if type(time_at_point) is datetime:                     # if a time is given, take forecast from nearest hour to that time
        difference = time_at_point - rounded_time
        difference = difference.total_seconds()//60
        rounder = str(round(difference / 60))
        if int(rounder) > 24 or int(rounder) < 0:
            sys.exit("Time given is out of window")

    elif actual_time.minute > 30:                           # if no time is given, just take forecast from nearest full hour
        rounder += 1

    rounded_time = str(rounded_time)
    rounded_time = rounded_time.replace("-", "")
    rounded_time = rounded_time.replace(":", "")

    return rounded_time, rounder


#################################
#        Get Modellevel         #
#################################


def get_modellevel_from_altitude(index, alt):        # Returns the fulllevel which is closest to the given altitude

    HHLs = []                                       # List of altitudes of all halflevels
    HFLs = []                                       # List of altitudes of all fulllevels

    i = 1
    while True:                                     # Get values for all halflevels
        try:
            HHL = read_value_from_gribfile(f"{ICON_switcher}_HHL_level_{i}.grib2", index)
            HHLs.append(HHL)
        except:
            break
        finally:
            i += 1

    for i in range(0, len(HHLs) - 1):                          # Calculate fulllevels from halflevels
        HFL = (HHLs[i] + HHLs[i+1])/2
        HFLs.append(HFL)

    level = min(range(len(HFLs)), key=lambda i: abs(HFLs[i] - alt)) + 1

    return level


#################################
#         Download HHL          #
#################################


def download_HHL():                                 # This function should only be executed once at the beginning. The HHL_level files are stored locally and can be accessed anytime

    global oldermodel                                # HHL is time-invariant, so it's not necessary to check whether the latest model is available. It's easier to just download an older file.
    oldermodel = True

    rounded_time = round_down_time(0)

    date = rounded_time[0][0:8]
    hour = rounded_time[0][9:11]

    i = 1
    while True:
        try:
            ICON_switcher = "D2"
            url = f"https://opendata.dwd.de/weather/nwp/icon-d2/grib/{hour}/hhl/icon-d2_germany_regular-lat-lon" \
                  f"_time-invariant_{date}{hour}_000_{i}_hhl.grib2.bz2"

            urllib.request.urlretrieve(url, f"{ICON_switcher}_HHL_level_{i}.grib2.bz2")

            unzip_file(f"{ICON_switcher}_HHL_level_{i}.grib2.bz2")
        except:
            break
        finally:
            i += 1

    i = 1
    while True:
        try:
            ICON_switcher = "EU"
            url = f"https://opendata.dwd.de/weather/nwp/icon-eu/grib/{hour}/hhl/icon-eu_europe_regular-lat-lon_" \
                  f"time-invariant_{date}{hour}_{i}_HHL.grib2.bz2"
            urllib.request.urlretrieve(url, f"{ICON_switcher}_HHL_level_{i}.grib2.bz2")

            unzip_file(f"{ICON_switcher}_HHL_level_{i}.grib2.bz2")
        except:
            break
        finally:
            i += 1

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
#        Getting index          #
#################################

def get_index_from_gribfile(file, lat, lon):
    value = eccodes_get_nearest.main(file, lat, lon)
    return value

#################################
#           Reading             #
#################################


def read_value_from_gribfile(file, index):
    f = open(os.path.join(sys.path[0], file), 'rb')
    gid = codes_grib_new_from_file(f)

    value = codes_get_values(gid)

    codes_release(gid)
    f.close()

    return value[index]


#################################
#      Remove old files         #
#################################


def remove_old_files():                     # removes any variable-file that is older than 4 hours

    for file in os.listdir('.'):
        if fnmatch.fnmatch(file, '*regular-lat-lon*'):
            file_age = (time.time() - os.path.getmtime(file))/3600
            if file_age > 4:
                os.remove(file)


#################################
#             Main              #
#################################


def main():

    # download_HHL()                # This function should only be executed once at the beginning. The HHL_level files are stored locally and can be accessed anytime

    variables_of_interest = ["t", "p", "qv", "u", "v", "w"]

    points_in_space = ((52.31588730661351, 4.778950137403114, 0), (52.31588730661351, 4.778950137403114, 0, 2021, 12, 7, 21, 55))
    # points_in_space = points_simulator()


    for point in points_in_space:

        global ICON_switcher
        ICON_switcher = "D2"

        lat, lon, alt = point[0], point[1], point[2]
        if len(point) > 3:
            time_at_point = datetime(point[3], point[4], point[5], point[6], point[7])
            print(time_at_point)
        else:
            time_at_point = 0
            print("Current time taken")

        if 44 <= lat <= 50:
            if not 0 <= lon <= 17:
                ICON_switcher = "EU"
        elif 50 < lat <= 57:
            if not -1.5 <= lon <= 18.5 and not 358.5 <= lon:
                ICON_switcher = "EU"
        else:
            ICON_switcher = "EU"

        index = get_index_from_gribfile(f"{ICON_switcher}_HHL_level_1.grib2", lat, lon)

        lvl = get_modellevel_from_altitude(index, alt)

        print("Point:", point, "// Model taken:", ICON_switcher, "// Level:", lvl)

        for var in variables_of_interest:

            global oldermodel                       # used if latest model is not yet available
            oldermodel = False

            try:                                                       # check if file is already present
                filename = build_url(lvl, var, time_at_point)[1][:-4]
                value = read_value_from_gribfile(filename, index)

            except:                                                    # if not, check if file of older model is present
                try:
                    oldermodel = True

                    filename = build_url(lvl, var, time_at_point)[1][:-4]
                    value = read_value_from_gribfile(filename, index)

                except:                                                # if both files are not yet present, download
                    oldermodel = False

                    download(lvl, var, time_at_point)
                    filename = build_url(lvl, var, time_at_point)[1][:-4]
                    value = read_value_from_gribfile(filename, index)

            print(f"{var} = ", value)

    remove_old_files()


def points_simulator():

    points_in_space = []

    alt = 0
    for i in range(100):
        points_in_space.append((52.31588730661351, 4.778950137403114, alt))
        alt += 17
        points_in_space.append((52.31588730661351, 4.778950137403114, alt, 2021, 12, 7, 17, 55))
        alt += 17
        i += 1

    return points_in_space


if __name__ == '__main__':
    sys.exit(main())
