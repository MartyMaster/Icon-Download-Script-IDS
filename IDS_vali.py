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
import pandas as pd


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

    if HHL_counter > 126:
        return

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


#################################
#        Getting index          #
#################################

def get_index_from_gribfile(file, lat, lon):
    """
    Calls eccodes_get_nearest.py which gives the index of the nearest point for any lat-lon-coordinate.
    """
    index = eccodes_get_nearest.main(file, lat, lon)
    return index


#################################
#        Get Modellevel         #
#################################

def get_modellevel_from_altitude(index, alt):
    """
    Returns the fulllevel which is closest to the given altitude at given index. This function works with a try/except
    block, because the ICON-D2 and the ICON-EU models do not have the same amount of levels.

    :param index
    :param alt
    :return: level
    """

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
#          Download             #
#################################

def download(lvl, var, time_at_point):
    """
    Checks if latest model is already available and downloads it. If not, it downloads the previous model.
    """

    try:
        url, filename = build_url(lvl, var, time_at_point)[:2]
        urllib.request.urlretrieve(url, filename)
    except:
        global oldermodel
        oldermodel = True

        url, filename, day, hour = build_url(lvl, var, time_at_point)
        subdir = day + "_" + hour
        filedir = os.path.join(parentdir, subdir)

        try:
            os.mkdir(filedir, mode=0o777)
        except:
            pass

        os.chdir(filedir)
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

    return url, filename, date, hour


def round_down_time(time_at_point):
    """
    Takes current UTC and rounds down to a 3hour interval. This is the update cycle of ICON-D2.

    :param time_at_point
    :return rounded_time
    :return rounder (The amount of hours by which time is rounded down. This is used to get the forecasthour)
    """

    actual_time = datetime.utcnow()

    # CAUTION: following line might lead to outdated information an shall only used for this validation purpose
    actual_time = time_at_point - timedelta(hours=1)

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
        if int(rounder) > 24 or int(rounder) < 0:
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

    filepath = os.path.join(os.getcwd(), file)

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

    f = open(os.path.join(os.getcwd(), file), 'rb')
    gid = codes_grib_new_from_file(f)

    value = codes_get_values(gid)

    codes_release(gid)
    f.close()

    return value[index]

#################################
#      Write to a csv-file      #
#################################

def write_to_csv(data, flightnr):
    header = ["Latitude", "Longitude", "geometric Altitude (m)", "UTC", "Level", "t", "p", "qv", "u", "v", "w"]

    time = datetime.utcnow()
    time = str(time.replace(microsecond=0))
    time = time.replace("-", "_")
    time = time.replace(":", "_")
    time = time.replace(" ","_")

    filename = f"flight{flightnr}_IDSminus1h.csv"

    filedir = os.path.join(parentdir, "IDSdata")
    os.chdir(filedir)

    with open(filename, 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f, delimiter=",")

        # write the header
        writer.writerow(header)

        # write multiple rows
        writer.writerows(data)

    print(f"flight{flightnr} saved into csv")
    os.chdir(parentdir)

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

def main(flightrows, flightnr):

    download_HHL()

    variables_of_interest = ["t", "p", "qv", "u", "v", "w"]

    """
    Insert here the points of interest, format: latitude, longitude, altitude in meters abv sealevel.
    Optional argument: time within the next 24h in UTC, format  YYYY, MM, DD, HH MM.
    """
    points_in_space = ((47.5642463503402, 8.0058731854457, 3115.711, 2022, 11, 17, 14, 15),)
    # points_in_space = points_simulator()
    points_in_space = read_from_txt(flightrows)

    csvdata = []
    global parentdir
    parentdir = os.getcwd()

    for point in points_in_space:

        global ICON_switcher
        ICON_switcher = "D2"

        # Decode point-tuples into their parameters:
        lat, lon, alt = point[0], point[1], point[2]
        if len(point) > 3:
            time_at_point = datetime(point[3], point[4], point[5], point[6], point[7])
            # print(time_at_point)
        else:
            time_at_point = 0
            # print("Current time taken")

        # Check if coordinates are within ICON-D2 range. Otherwise use ICON-EU
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

        csvrow = [lat, lon, alt, time_at_point, lvl]

        for var in variables_of_interest:

            os.chdir(parentdir)

            global oldermodel                       # used if latest model is not yet available
            oldermodel = False

            try:                                                       # check if file is already present
                filename, day, hour = build_url(lvl, var, time_at_point)[1:4]
                subdir = day + "_" + hour
                filedir = os.path.join(parentdir, subdir)
                os.chdir(filedir)
                try:
                    unzip_file(filename)
                except:
                    pass
                filename = filename[:-4]
                value = read_value_from_gribfile(filename, index)
                os.chdir(parentdir)

            except:                                                    # if not, check if file of older model is present
                try:
                    oldermodel = True

                    os.chdir(parentdir)
                    filename, day, hour = build_url(lvl, var, time_at_point)[1:4]
                    filename = filename[:-4]
                    subdir = day + "_" + hour
                    filedir = os.path.join(parentdir, subdir)
                    os.chdir(filedir)
                    value = read_value_from_gribfile(filename, index)
                    os.chdir(parentdir)

                except:                                                # if both files are not yet present, download
                    oldermodel = False

                    os.chdir(parentdir)
                    filename, day, hour = build_url(lvl, var, time_at_point)[1:4]
                    filename = filename[:-4]
                    subdir = day + "_" + hour
                    filedir = os.path.join(parentdir, subdir)

                    try:
                        os.mkdir(filedir, mode=0o777)
                    except:
                        pass

                    os.chdir(filedir)
                    download(lvl, var, time_at_point)
                    value = read_value_from_gribfile(filename, index)
                    os.chdir(parentdir)

            # print(f"{var} = ", value)

            csvrow.append(value)

        csvdata.append(csvrow)

    write_to_csv(csvdata, flightnr)


#################################
# Functions used for validation #
#################################


def points_simulator():

    points_in_space = []

    alt = 400
    for i in range(3):
        points_in_space.append((47.45782369382128, 8.551156219956459, alt, 2022, 1, 20, 19, 6))
        alt += 15
        i += 1

    return points_in_space


def read_from_txt(flightrows):

    points_in_space = []

    for index, row in flightrows.iterrows():
        lat = row["P860: Latitude (degrees)"]
        lon = row["P860: Longitude (degrees)"]
        alt = row["P860: GPS Altitude (ft)"]
        alt_meter = alt * 0.3048
        date = row["Flight Date (Exact) (UTC)"]
        year = 2022
        if "Sep" in date:
            month = 9
        elif "Oct" in date:
            month = 10
        if "Nov" in date:
            month = 11
        day = int(date.partition(" ")[0])
        time_hour = round(row["P860: GMT"], 2)
        hours = int(time_hour)
        minutes = int((time_hour * 60) % 60)

        if 44 <= lat <= 50 and 6 <= lon <= 10 and 380 <= alt_meter <= 4000 and time_hour <= 24:
            points_in_space.append((lat, lon, alt_meter, year, month, day, hours, minutes))

    return points_in_space


def main_looper():
    file = pd.read_csv("20221116_data_export_Martin_Jansen_ZHAW_4.txt", sep="\t", header=0)

    flightlist = []
    for flightnr in file["Flight Record"]:
        if flightnr not in flightlist:
            flightlist.append(flightnr)

    for flightnr in flightlist:
        flightrows = file.loc[file["Flight Record"] == flightnr]
        main(flightrows, flightnr)


if __name__ == '__main__':
    # sys.exit(main())
    sys.exit(main_looper())
