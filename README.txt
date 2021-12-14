
This python script is developped by Martin Jansen, student for the MSE in Aviation at ZHAW, during the specialisation project 1 (VT1).
It's purpose is to provide forecast weather data of certain variables of interest for operational use within the LNAS project developped at DLR.

What it does: For every given point, consisting of latitude, longitude and altitude in meters abv sealevel, it downloads the forecast values out of the ICON-DE and ICON-EU models
	from the open data server of DWD. An optional argument time within the next 24h in UTC can be accepted. If no time is provided, the current time is considered.
	Currently the variables are temperature T, pressure P, specific humidity QV and windspeed in all three directions U, V, W.

Prerequisites:
	This script is run with a python interpreter under Windows Subsystem for Linux WSL.
	Software package ecCodes is required to run this script: https://confluence.ecmwf.int/pages/viewpage.action?pageId=45757987
	See also requirements.txt