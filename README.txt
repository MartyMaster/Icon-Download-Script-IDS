
This python script is developped by Martin Jansen, student for the MSE in Aviation at ZHAW, during the specialisation projects 1 and 2 (VT1 & VT2).
Its purpose is to provide forecast weather data of certain variables of interest for operational use within the LNAS project developped by DLR.

What it does: For every given point, consisting of latitude, longitude and altitude in meters above sealevel, it downloads the forecast values out of the ICON-DE and ICON-EU models from the open data server of DWD. An optional time argument within the next 24h in UTC can be accepted. If no time is provided, the current time is considered. Currently the variables are temperature T, pressure P, specific humidity QV and windspeed in all three directions U, V, W.

There is a second branch with interpolation functions. Horizontal, vertical and temporal interpolations are added and can be used either separately or combined.
The two branches "validation" and "interpolation_validation" were used for validating on the ZHAW internal server and are of no use outside this environment.

What you need to do: 
Main branch: Insert the points of interest on line 306 and run the script. Output will be stored in a csv with the current time as name.
Interpolatin branch: Insert the points of interest on line 347 and run the script. Optionally, deactivate certain interpolation functions according to your needs. For this, adapt (comment or uncomment) the code between lines 392-399 and 440-485 according to the comments in the code.

Prerequisites:
	This script is run with a python interpreter under Windows Subsystem for Linux WSL.
	Software package ecCodes is required to run this script: https://confluence.ecmwf.int/pages/viewpage.action?pageId=45757987
	See also requirements.txt
	
Data source: 
https://opendata.dwd.de/weather/nwp/

