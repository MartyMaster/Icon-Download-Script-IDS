import urllib.request
import requests
import datetime
from datetime import datetime, timedelta
import bz2
import pandas as pd
import os
import sys
import eccodes_get_nearest


#################################       # Assumption: the latest model will give the most accurate forecast
#          Download             #
#################################


def download(altitude):
    url = build_url(altitude)
    urllib.request.urlretrieve(url, "ICON.grib2.bz2")


def build_url(altitude):
    date = get_latest_model_date()
    hour = get_latest_model_hour()
    forecast_time = get_forecast_time()
    modellevel = get_modellevel_from_altitude(altitude)
    variable = get_variable()

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
        rounder = 3
    elif a == 1 or a == 4 or a == 7 or a == 10 or a == 13 or a == 16 or a == 19 or a == 22:
        rounder = 4
    else:
        rounder = 2

    rounded_time = str(actual_time.replace(microsecond=0, second=0, minute=0) - timedelta(hours=rounder))
    rounded_time = rounded_time.replace("-", "")
    rounded_time = rounded_time.replace(":", "")

    return rounded_time, rounder


#################################
#        Get Modellevel         #
#################################


def get_elevation(lat, long):                   # function for returning elevation from lat, long, based on open elevation data, which in turn is based on SRTM
    query = ('https://api.open-elevation.com/api/v1/lookup'
             f'?locations={lat},{long}')

    r = requests.get(query).json()
    elevation = pd.json_normalize(r, 'results')['elevation'].values[0]

    date = get_latest_model_date()
    hour = get_latest_model_hour()

    url = f"https://opendata.dwd.de/weather/nwp/icon-d2/grib/{hour}/hsurf/icon-d2_germany_regular-lat-lon_time-invariant_{date}{hour}_000_0_hsurf.grib2.bz2"
    urllib.request.urlretrieve(url, f"hsurf.grib2.bz2")

    unzip_file(f"hsurf.grib2.bz2")

    return elevation

#def get_elevation_from_hsurf(lat, long):



def download_HHL():
    date = get_latest_model_date()
    hour = get_latest_model_hour()

    for i in range(1, 67):
        url = f"https://opendata.dwd.de/weather/nwp/icon-d2/grib/{hour}/hhl/icon-d2_germany_regular-lat-lon_time-invariant_{date}{hour}_000_{i}_hhl.grib2.bz2"
        urllib.request.urlretrieve(url, f"HHL_level_{i}.grib2.bz2")

        unzip_file(f"HHL_level_{i}.grib2.bz2")


    #for i in range(1, 67):
    #    os.remove(os.path.join(sys.path[0], f"HHL_level_{i}.grib2"))


def get_modellevel_from_altitude(altitude):

    HHLs = []                                       # List of altitudes of all halflevels
    HFLs = []                                       # List of altitudes of all fulllevels

    for i in range(1, 67):                          # Get values for all halflevels
        HHL = eccodes_get_nearest.main(f"HHL_level_{i}.grib2", 51.71327675049083, 3.3868447313078023)
        HHLs.append(HHL)
        #alt_of_full_lvl = HHL
        #print(alt_of_full_lvl)
    print(HHLs)

    for i in range(0, 65):                          # Calculate fulllevels from halflevels
        HFL = (HHLs[i] + HHLs[i+1])/2
        HFLs.append(HFL)
    print(HFLs)

    level = min(range(len(HFLs)), key=lambda i: abs(HFLs[i] - altitude)) + 1

    print(level)
    return level


def get_variable():
    return "u"


#################################
#          Unzipping            #
#################################


def unzip_file(file):
    filepath = os.path.join(sys.path[0], file)

    comp_file = bz2.BZ2File(filepath)

    data = comp_file.read()                         # get the decompressed data
    newfilepath = filepath[:-4]                     # assuming the filepath ends with .bz2

    open(newfilepath, 'wb').write(data)             # write an uncompressed file

    os.remove(filepath)                             #remove the compressed file directly


#################################
#           Reading             #
#################################

# read grib2-file with ecCodes


#################################
#             Main              #
#################################


def main():
    get_modellevel_from_altitude(1100)
    #download()
    #unzip_file("ICON.grib2.bz2")
    #download_HHL()



if __name__ == '__main__':
    sys.exit(main())
