import urllib.request
from datetime import datetime, timedelta
import time
import bz2
import os
import sys
import eccodes_get_nearest
from eccodes import *
import fnmatch
import csv
import math


#################################
#         Download HHL          #
#################################

def download_HHL():
    """
    Checks if enough HHL-files are present. If not it downloads them.
    """

    HHL_counter = 0
    for file in os.listdir('.'):
        if fnmatch.fnmatch(file, '*HHL_level*'):
            HHL_counter += 1

    if HHL_counter <= 126:

        global oldermodel                  # HHL is time-invariant, so it's not necessary to check whether the latest model
        oldermodel = True                  # is available. It's easier to just download an older file.

        rounded_time = round_down_time(0)

        date = rounded_time[0][0:8]
        hour = rounded_time[0][9:11]

        for i in range(1, 67):
            url = f"https://opendata.dwd.de/weather/nwp/icon-d2/grib/{hour}/hhl/icon-d2_germany_regular-lat-lon" \
                  f"_time-invariant_{date}{hour}_000_{i}_hhl.grib2.bz2"
            urllib.request.urlretrieve(url, f"D2_HHL_level_{i}.grib2.bz2")
            unzip_file(f"D2_HHL_level_{i}.grib2.bz2")
            i += 1

        for i in range(1, 62):
            url = f"https://opendata.dwd.de/weather/nwp/icon-eu/grib/{hour}/hhl/icon-eu_europe_regular-lat-lon_" \
                  f"time-invariant_{date}{hour}_{i}_HHL.grib2.bz2"
            urllib.request.urlretrieve(url, f"EU_HHL_level_{i}.grib2.bz2")
            unzip_file(f"EU_HHL_level_{i}.grib2.bz2")
            i += 1

    D2_HHls = []
    EU_HHLs = []

    for i in range(1, 67):
        f = open(os.path.join(os.getcwd(), f"D2_HHL_level_{i}.grib2"), 'rb')
        gid = codes_grib_new_from_file(f)
        D2_HHls.append(codes_get_values(gid))
        codes_release(gid)
        f.close()

    for i in range(1, 62):
        f = open(os.path.join(os.getcwd(), f"EU_HHL_level_{i}.grib2"), 'rb')
        gid = codes_grib_new_from_file(f)
        EU_HHLs.append(codes_get_values(gid))
        codes_release(gid)
        f.close()

    return D2_HHls, EU_HHLs


#################################
#        Getting index          #
#################################

def get_index_from_gribfile(file, lat, lon):
    """
    Calls eccodes_get_nearest.py which gives the index of the nearest point for any lat-lon-coordinate.
    """
    nearest = eccodes_get_nearest.main(file, lat, lon)

    distances = []
    indices = []
    for pt in nearest:
        distances.append(pt.distance)
        indices.append(pt.index)

    nearest = sorted(zip(distances, indices))

    distances = []
    indices = []
    for pt in nearest:
        distances.append(pt[0])
        indices.append(pt[1])

    return distances, indices


#################################
#        Get Modellevel         #
#################################

def get_modellevel_from_altitude(inputHHLs, index, alt):
    """
    Returns the fulllevel which is closest to the given altitude at given index. This function works with a try/except
    block, because the ICON-D2 and the ICON-EU models do not have the same amount of levels.

    :param index
    :param alt
    :return: level
    """

    HHLs = []                                       # List of altitudes of all halflevels
    HFLs = []                                       # List of altitudes of all fulllevels

    i = 0
    while True:                                     # Get values for all halflevels
        try:
            HHLs.append(inputHHLs[i][index])
        except:
            break
        finally:
            i += 1

    for i in range(0, len(HHLs) - 1):                          # Calculate fulllevels from halflevels
        HFL = (HHLs[i] + HHLs[i+1])/2
        HFLs.append(HFL)

    level = min(range(len(HFLs)), key=lambda i: abs(HFLs[i] - alt)) + 1

    level_list = [level]
    alt_list = []

    if level == 1:                                         # add levels above or below for lateral linear interpolation
        level_list.append(2)
    elif level == 65 and ICON_switcher == "D2":
        level_list.append(64)
    elif level == 60 and ICON_switcher == "EU":
        level_list.append(59)
    else:
        if (HFLs[level-1] - alt) < 0:
            level_list.append(level - 1)
        else:
            level_list.append(level + 1)

    for i in level_list:
        alt_list.append(HFLs[i-1])

    return level, level_list, alt_list


#################################
#          Download             #
#################################

def download(lvl, var, time_at_point):
    """
    Checks if latest model is already available and downloads it. If not, it downloads the previous model.
    """

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
    forecast_time = str(rounded_time[1]).zfill(3)               # fill with 0 until string is 3 digits long

    modellevel = lvl
    variable = var

    if ICON_switcher == "D2":
        filename = f"icon-d2_germany_regular-lat-lon_model-level_{date}{hour}_{forecast_time}_{modellevel}_" \
                   f"{variable}.grib2.bz2"
        url = f"https://opendata.dwd.de/weather/nwp/icon-d2/grib/{hour}/{variable}/{filename}"
    elif ICON_switcher == "EU":
        filename = f"icon-eu_europe_regular-lat-lon_model-level_{date}{hour}_{forecast_time}_{modellevel}_" \
                   f"{variable.upper()}.grib2.bz2"
        url = f"https://opendata.dwd.de/weather/nwp/icon-eu/grib/{hour}/{variable}/{filename}"

    return url, filename


def round_down_time(time_at_point):
    """
    Takes current UTC and rounds down to a 3hour interval. This is the update cycle of ICON-D2.

    :param time_at_point
    :return rounded_time
    :return rounder (The amount of hours by which time is rounded down. This is used to get the forecasthour)
    """

    actual_time = datetime.utcnow()
    a = actual_time.hour

    if a == 0 or a == 3 or a == 6 or a == 9 or a == 12 or a == 15 or a == 18 or a == 21:
        rounder = 0
    elif a == 1 or a == 4 or a == 7 or a == 10 or a == 13 or a == 16 or a == 19 or a == 22:
        rounder = 1
    else:
        rounder = 2

    if oldermodel:                               # if latest model is not yet available take the one from 3 hours before
        rounder += 3

    rounded_time = actual_time.replace(microsecond=0, second=0, minute=0) - timedelta(hours=rounder)

    if type(time_at_point) is datetime:               # if a time is given, take forecast from nearest hour to that time
        difference = time_at_point - rounded_time
        difference = difference.total_seconds()//60
        rounder = str(round(difference / 60))
        if int(rounder) > 27 or int(rounder) < 0:
            sys.exit("Time given is out of window")

    elif actual_time.minute > 30:                       # if no time is given, just take forecast from nearest full hour
        rounder += 1

    rounded_time = str(rounded_time)
    rounded_time = rounded_time.replace("-", "")
    rounded_time = rounded_time.replace(":", "")

    return rounded_time, rounder


#################################
#          Unzipping            #
#################################

def unzip_file(file):
    """
    Takes a bz2-file and unzips it
    """

    filepath = os.path.join(sys.path[0], file)

    comp_file = bz2.BZ2File(filepath)

    data = comp_file.read()                         # get the decompressed data
    newfilepath = filepath[:-4]                     # assuming the filepath ends with .bz2

    open(newfilepath, 'wb').write(data)             # write an uncompressed file

    os.remove(filepath)                             # remove the compressed file directly


#################################
#           Reading             #
#################################

def read_value_from_gribfile(file, index):
    """
    Returns the value at the given index in given file using ecCodes.

    :param file
    :param index
    :return: value at index
    """

    f = open(os.path.join(sys.path[0], file), 'rb')
    gid = codes_grib_new_from_file(f)

    value = codes_get_values(gid)

    codes_release(gid)
    f.close()

    return value[index]

#################################
#      Write to a csv-file      #
#################################

def write_to_csv(data):
    header = ["Latitude", "Longitude", "geometric Altitude (m)", "UTC", "Level", "t", "p", "qv", "u", "v", "w"]

    time = datetime.utcnow()
    time = str(time.replace(microsecond=0))
    time = time.replace("-", "_")
    time = time.replace(":", "_")
    time = time.replace(" ","_")
    filename = f"{time}.csv"

    with open(filename, 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f, delimiter=",")

        # write the header
        writer.writerow(header)

        # write multiple rows
        writer.writerows(data)


#################################
#      Remove old files         #
#################################

def remove_old_files():
    """
    Removes any variable-file that is older than 4 hours
    """

    warnings.warn("WARNING: You are about to remove all downloaded files aged more than 4 hours. "
                  "If you're sure about that, uncomment the exit-statement below and run this function/script again.")
    exit()

    for file in os.listdir('.'):
        if fnmatch.fnmatch(file, '*regular-lat-lon*'):
            file_age = (time.time() - os.path.getmtime(file))/3600
            if file_age > 4:
                os.remove(file)


#################################
#             Main              #
#################################

def main():

    D2_HHLs, EU_HHLs = download_HHL()

    variables_of_interest = ["t", "p", "qv", "u", "v", "w"]

    """
    Insert here the points of interest, format: latitude, longitude, altitude in meters abv sealevel.
    Optional argument: time within the next 24h in UTC, format  YYYY, MM, DD, HH MM.
    """
    points_in_space = ((47.5642463503402, 8.0058731854457, 0),)
    # points_in_space = points_simulator()

    csvdata = []

    for point in points_in_space:

        global ICON_switcher
        ICON_switcher = "D2"

        # Decode point-tuples into their parameters:
        lat, lon, alt = point[0], point[1], point[2]
        if len(point) > 3:
            time_at_point = datetime(point[3], point[4], point[5], point[6], point[7])
            print(time_at_point)
        else:
            time_at_point = datetime.utcnow()
            print("Current time taken")

        # Check if coordinates are within ICON-D2 range. Otherwise use ICON-EU
        if 44 <= lat <= 50:
            if not 0 <= lon <= 17:
                ICON_switcher = "EU"
        elif 50 < lat <= 57:
            if not -1.5 <= lon <= 18.5 and not 358.5 <= lon:
                ICON_switcher = "EU"
        else:
            ICON_switcher = "EU"

        # lat,lon,alt,index,lvl describe the actual point. All lists starting with grid... describe the grid points
        griddistances, gridindices = get_index_from_gribfile(f"{ICON_switcher}_HHL_level_1.grib2", lat, lon)
        index = gridindices[0]

        if ICON_switcher == "D2":
            lvl, level_list, alt_list = get_modellevel_from_altitude(D2_HHLs, index, alt)
        else:
            lvl, level_list, alt_list = get_modellevel_from_altitude(EU_HHLs, index, alt)

        gridalts = []
        for gridlevel in level_list:
            for gridindex in gridindices:                                   # calculate alt of full levels from HHLs
                gridalt1 = read_value_from_gribfile(f"{ICON_switcher}_HHL_level_{gridlevel}.grib2", gridindex)
                gridalt2 = read_value_from_gribfile(f"{ICON_switcher}_HHL_level_{gridlevel + 1}.grib2", gridindex)
                gridalts.append((gridalt1 + gridalt2)/2)

        print("Point:", point, "// Model taken:", ICON_switcher, "// Level:", lvl)

        csvrow = [lat, lon, alt, time_at_point, lvl]

        for var in variables_of_interest:

            value_list = []

            for level in level_list:

                global oldermodel                       # used if latest model is not yet available
                oldermodel = False

                try:                                                       # check if file is already present
                    filename = build_url(level, var, time_at_point)[1][:-4]
                    for gridindex in gridindices:
                        value_list.append(read_value_from_gribfile(filename, gridindex))

                except:                                               # if not, check if file of older model is present
                    try:
                        oldermodel = True

                        filename = build_url(level, var, time_at_point)[1][:-4]
                        for gridindex in gridindices:
                            value_list.append(read_value_from_gribfile(filename, gridindex))

                    except:                                                # if both files are not yet present, download
                        oldermodel = False

                        download(level, var, time_at_point)
                        filename = build_url(level, var, time_at_point)[1][:-4]
                        for gridindex in gridindices:
                            value_list.append(read_value_from_gribfile(filename, gridindex))

            # calculate actual distances from grid-distances and alts using pythagoras
            act_distances = []
            for altitude in alt_list:
                for dist in griddistances:
                    act_distances.append(math.sqrt((dist*1000)**2 + (altitude-alt)**2))

            # interpolate value using "inverted distance weighting IDW"
            nominator = 0
            denominator = 0
            for i in range(len(value_list)):
                nominator += (value_list[i] / act_distances[i])
                denominator += (1 / act_distances[i])
            value = nominator / denominator

            print(f"{var} = ", value, ", interpolated from list: ", value_list)

            csvrow.append(value)

        csvdata.append(csvrow)

    write_to_csv(csvdata)


def points_simulator():

    points_in_space = []

    alt = 400
    for i in range(3):
        points_in_space.append((47.45782369382128, 8.551156219956459, alt))
        alt += 500
        i += 1

    return points_in_space


if __name__ == '__main__':
    sys.exit(main())
