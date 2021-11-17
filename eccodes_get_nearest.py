#
# (C) Copyright 2005- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

from __future__ import print_function
import traceback
import sys
import os

from eccodes import *

#INPUT = os.path.join(sys.path[0], 'hsurf.grib2')
VERBOSE = 1  # verbose error reporting


def get_nearest(input_file, input_lat, input_lon):
    # points = ((51.71327675049083, 3.3868447313078023), (47.4644997606922, 8.54656742778482))      # if several points would be needed

    f = open(os.path.join(sys.path[0], input_file), 'rb')
    gid = codes_grib_new_from_file(f)

    # for lat, lon in points:                                                                        # if several points would be needed
    nearest = codes_grib_find_nearest(gid, input_lat, input_lon)[0]
        #print(lat, lon)
        #print(nearest.lat, nearest.lon, nearest.value, nearest.distance,
        #      nearest.index)

        #four = codes_grib_find_nearest(gid, lat, lon, is_lsm=False, npoints=1)
        #for i in range(len(four)):
        #    print("- %d -" % i)
        #    print(four[i])

        #print("-" * 100)

    codes_release(gid)
    f.close()

    return nearest.value


def main(input_file, input_lat, input_lon):
    try:
        return get_nearest(input_file, input_lat, input_lon)
    except CodesInternalError as err:
        if VERBOSE:
            traceback.print_exc(file=sys.stderr)
        else:
            sys.stderr.write(err.msg + '\n')

        return 1


if __name__ == "__main__":
    sys.exit(main())