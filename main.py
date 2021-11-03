import urllib.request
import datetime

# import eccodes
# import bunzip2
from datetime import date
from typing import Type


def download():
    url = build_url()
    urllib.request.urlretrieve(url, "download4.grib2.bz2")


def build_url():
    date = get_latest_model_date()
    hour = get_latest_model_hour()
    forecast_time = get_forecast_time()
    modellevel = get_modellevel()
    variable = get_variable()
    url = f"https://opendata.dwd.de/weather/nwp/icon-d2/grib/{hour}/{variable}" \
          f"/icon-d2_germany_regular-lat-lon_model-level_{date}{hour}_{forecast_time}_{modellevel}_{variable}.grib2.bz2"
    return url



def get_latest_model_date():
    #date = datetime.isoformat
    #print(date)
    return "20211103"


def get_latest_model_hour():
    return "00"


def get_forecast_time():
    return "000"


def get_modellevel():
    return "1"

def get_variable():
    return "u"

if __name__ == '__main__':
    download()
