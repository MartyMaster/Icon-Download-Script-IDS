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

        global oldermodel               # HHL is time-invariant, so it's not necessary to check whether the latest model
        oldermodel = True               # is available. It's easier to just download an older file.

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

    # All HHL files are stored in a list per model, which can be accessed everytime a level is needed.
    # This gives better performance than opening all HHL files for every point.

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

    # sorting the nearest-list to: from nearest to furthest point
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

    if level == 1:                                         # add levels above or below for vertical interpolation
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

    difference = time_at_point - rounded_time
    difference = difference.total_seconds()//60 + 0.1
    rounder = str(round(difference / 60))
    if int(rounder) > 24 or int(rounder) < 0:
        sys.exit("Time given is out of window")

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
    header = ["Latitude", "Longitude", "geometric Altitude (m)", "UTC", "exactGMT", "Level", "t", "p", "qv", "u", "v", "w"]
    # This next line is only for speeding up validation, where qv and w are not needed. Be sure to adjust in main()
    # header = ["Latitude", "Longitude", "geometric Altitude (m)", "UTC", "exactGMT", "Level", "t", "p", "u", "v"]

    time = datetime.utcnow()
    time = str(time.replace(microsecond=0))
    time = time.replace("-", "_")
    time = time.replace(":", "_")
    time = time.replace(" ", "_")

    filename = f"flight{flightnr}_IDSminus1h_IDW_horizontal_interpol.csv"

    filedir = os.path.join(parentdir, "IDSdata")
    os.chdir(filedir)

    with open(filename, 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f, delimiter=",")

        # write the header
        writer.writerow(header)

        # write multiple rows
        writer.writerows(data)

    # print(f"flight{flightnr} saved into csv")
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

    D2_HHLs, EU_HHLs = download_HHL()

    variables_of_interest = ["t", "p", "qv", "u", "v", "w"]
    # This next line is only for speeding up validation, where qv and w are not needed. Be sure to adjust in write_to_csv()
    # variables_of_interest = ["t", "p", "u", "v"]

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
        # for validation only EU
        # ICON_switcher = "EU"

        # Decode point-tuples into their parameters:
        lat, lon, alt, exactGMT = point[0], point[1], point[2], point[8]
        if len(point) > 3:
            time_at_point = datetime(point[3], point[4], point[5], point[6], point[7])
            # print(time_at_point)
        else:
            time_at_point = datetime.utcnow()
            # print("Current time taken")

        if time_at_point.minute >= 30:
            time_at_point2 = time_at_point - timedelta(minutes=30)
        else:
            time_at_point2 = time_at_point + timedelta(minutes=30)
        time_at_point_list = [time_at_point, time_at_point2]

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

        # WARNING: this next line is for horizontal interpolation only and will delete any vertical interpolation
        level_list.pop(1)
        # WARNING: this next lines are for vertical interpolation only and will delete any horizontal interpolation
        # gridindices.pop(1)
        # gridindices.pop(1)
        # gridindices.pop(1)
        # WARNING: this next line  will delete any time interpolation
        time_at_point_list.pop(1)

        """
        gridalts = []
        for gridlevel in level_list:
            for gridindex in gridindices:                                   # calculate alt of full levels from HHLs
                gridalt1 = read_value_from_gribfile(f"{ICON_switcher}_HHL_level_{gridlevel}.grib2", gridindex)
                gridalt2 = read_value_from_gribfile(f"{ICON_switcher}_HHL_level_{gridlevel + 1}.grib2", gridindex)
                gridalts.append((gridalt1 + gridalt2)/2)
        """
        # print("Point:", point, "// Model taken:", ICON_switcher, "// Level:", lvl, "Gridalts:", gridalts)

        # following lines are for debugging of the new interpol only, they will mess up old interpol with pythagoras
        # gridalts.sort()
        # if abs(gridalts[0] - gridalts[3]) < 50: # set back to 50 or whatever there is to be used

        csvrow = [lat, lon, alt, time_at_point, exactGMT, lvl]

        for var in variables_of_interest:

            os.chdir(parentdir)

            value_time_list = []

            for time_at in time_at_point_list:

                value_list = []

                for level in level_list:

                    global oldermodel                       # used if latest model is not yet available
                    oldermodel = False

                    try:                                                       # check if file is already present
                        filename, day, hour = build_url(level, var, time_at)[1:4]
                        subdir = day + "_" + hour
                        filedir = os.path.join(parentdir, subdir)
                        os.chdir(filedir)
                        try:
                            unzip_file(filename)
                        except:
                            pass
                        filename = filename[:-4]
                        for gridindex in gridindices:
                            value_list.append(read_value_from_gribfile(filename, gridindex))
                        os.chdir(parentdir)

                    except:                                                # if not, check if file of older model is present
                        try:
                            oldermodel = True

                            os.chdir(parentdir)
                            filename, day, hour = build_url(level, var, time_at)[1:4]
                            filename = filename[:-4]
                            subdir = day + "_" + hour
                            filedir = os.path.join(parentdir, subdir)
                            os.chdir(filedir)
                            for gridindex in gridindices:
                                value_list.append(read_value_from_gribfile(filename, gridindex))
                            os.chdir(parentdir)

                        except:                                                # if both files are not yet present, download
                            oldermodel = False

                            os.chdir(parentdir)
                            filename, day, hour = build_url(level, var, time_at)[1:4]
                            filename = filename[:-4]
                            subdir = day + "_" + hour
                            filedir = os.path.join(parentdir, subdir)

                            try:
                                os.mkdir(filedir, mode=0o777)
                            except:
                                pass

                            os.chdir(filedir)
                            download(level, var, time_at)
                            for gridindex in gridindices:
                                value_list.append(read_value_from_gribfile(filename, gridindex))
                            os.chdir(parentdir)

                # old interpolation method with pythagoras:
                """
                # calculate actual distances from grid-distances and alts using pythagoras
                act_distances = []
                for i in range(len(griddistances)):
                    act_distances.append(math.sqrt((griddistances[i] * 1000) ** 2 + (gridalts[i] - alt) ** 2))
                for i in range(len(griddistances)):
                    act_distances.append(math.sqrt((griddistances[i] * 1000) ** 2 + (gridalts[i+4] - alt) ** 2))
    
                # interpolate value using "inverted distance weighting IDW"
                nominator = 0
                denominator = 0
                for i in range(len(value_list)):
                    nominator += (value_list[i] / act_distances[i])
                    denominator += (1 / act_distances[i])
                value = nominator / denominator                
                """

                # Interpolating values using "inverted distance weighting IDW" on both levels first
                nominator = 0
                denominator = 0
                for i in range(len(griddistances)):
                    nominator += (value_list[i] / griddistances[i])
                    denominator += (1 / griddistances[i])
                value_alt1 = nominator / denominator

                # for only horizontal interpolation
                value = value_alt1

                """
                nominator = 0
                denominator = 0
                for i in range(len(griddistances)):
                    nominator += (value_list[i+4] / griddistances[i])
                    denominator += (1 / griddistances[i])
                value_alt2 = nominator / denominator
                
                # for only vertical interpolation (and possibly time)
                value_alt1 = value_list[0]
                value_alt2 = value_list[1]

                # Another IDW between the levels for vertical interpolation
                value = ((value_alt1/abs(alt_list[0]-alt) + value_alt2/abs(alt_list[1]-alt)) / (1/abs(alt_list[0]-alt) + 1/abs(alt_list[1]-alt)))

                # for only time interpolation
                # value = value_list[0]

                # for Time interpolation
                # value_time_list.append(value)
            
            # Time interolation: weighting is 1/(minutes away from full hour)
            nominator = 0
            denominator = 0
            nominator += (value_time_list[0] / ((60 - time_at_point.minute) / 60))
            nominator += (value_time_list[1] / ((time_at_point.minute + 0.001) / 60))   # +0.001 to avoid division by zero
            denominator += (1 / ((time_at_point.minute + 0.001) / 60))
            denominator += (1 / ((60 - time_at_point.minute) / 60))
            value = nominator / denominator
            """
            print(f"{var} =  {value} , interpolated from valuelist: {value_list}")

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
    flightrows = flightrows.sort_values("P860: GMT", ascending=True)

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
        exactGMT = row["P860: GMT"]

        if 44 <= lat <= 50 and 6 <= lon <= 10 and 380 <= alt_meter <= 4000 and time_hour <= 24:
            points_in_space.append((lat, lon, alt_meter, year, month, day, hours, minutes, exactGMT))

    return points_in_space


def main_looper():
    starttime = datetime.utcnow()

    for i in range(1):
        file = pd.read_csv(f"20221116_data_export_Martin_Jansen_ZHAW_{i+2}.txt", sep="\t", header=0)
        file = pd.read_csv(f"20221116_data_export_Martin_Jansen_ZHAW_2.txt", sep="\t", header=0)

        flightlist = []
        for flightnr in file["Flight Record"]:
            if flightnr not in flightlist:
                flightlist.append(flightnr)

        # flightlist = [3091291]

        i = 0
        timer = []
        for flightnr in flightlist:
            starttime_point = datetime.utcnow()
            i += 1
            # print(flightnr)
            flightrows = file.loc[file["Flight Record"] == flightnr]
            main(flightrows, flightnr)
            endtime_point = datetime.utcnow()
            timer.append(endtime_point-starttime_point)

        avg = pd.to_timedelta(pd.Series(timer)).mean()

    print(f"IDS started at {starttime}, finished at {datetime.utcnow()}.\n"
          f"Horizontal interpol for {i} flights, avg time per flight: {avg}")


if __name__ == '__main__':
    # sys.exit(main())
    sys.exit(main_looper())
