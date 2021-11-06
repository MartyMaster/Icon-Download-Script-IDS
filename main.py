import urllib.request
import datetime
from datetime import datetime, timedelta


# import eccodes
# import bunzip2


def download():
    url = build_url()
    urllib.request.urlretrieve(url, "download.grib2.bz2")


def build_url():                                    # Assumption: the latest model will give the most accurate forecast
    date = get_latest_model_date()
    hour = get_latest_model_hour()
    forecast_time = get_forecast_time()
    modellevel = get_modellevel()
    variable = get_variable()
    url = f"https://opendata.dwd.de/weather/nwp/icon-d2/grib/{hour}/{variable}" \
          f"/icon-d2_germany_regular-lat-lon_model-level_{date}{hour}_{forecast_time}_{modellevel}_{variable}.grib2.bz2"
    return url


def get_latest_model_date():
    model_date = round_down_time()[0]       # use only first return, which is rounded_time
    return (model_date[0:8])                # use only first 8 characters, ie the date


def get_latest_model_hour():
    model_hour = round_down_time()[0]       # use only first return, which is rounded_time
    return (model_hour[9:11])               # use only characters 9 and 10, ie the hour


def get_forecast_time():
    forecast_time = round_down_time()[1]    # use only second return, which is rounder
    return f"00{forecast_time}"             # add 00 in front to be in line with DWD nummeration


def round_down_time():
    actual_time = datetime.utcnow()
    a = actual_time.hour
    if a == 0 or a == 3 or a == 6 or a == 9 or a == 12 or a == 15 or a == 18 or a == 21:
        rounder = 0
    elif a == 1 or a == 4 or a == 7 or a == 10 or a == 13 or a == 16 or a == 19 or a == 22:
        rounder = 1
    else:
        rounder = 2
    rounded_time = str(actual_time.replace(microsecond=0, second=0, minute=0) - timedelta(hours=rounder))
    rounded_time = rounded_time.replace("-","")
    rounded_time = rounded_time.replace(":","")
    return (rounded_time, rounder)


def get_modellevel():
    return "1"


def get_variable():
    return "u"


#def unzip_file():


if __name__ == '__main__':
    download()
    # unzip_file()

    print(round_down_time())
    print(get_latest_model_date())
    print(get_latest_model_hour())
    print(get_forecast_time())


