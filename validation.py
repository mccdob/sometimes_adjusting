# -*- coding: utf-8 -*-
"""
Created on Thu Feb 29 18:16:06 2024

@author: miran

Validation script

"""

import Main
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from RunSim import RunSim
from my_functions import readCaseStudyData


# Compare total modelled energy
# ------------
energy,dc,allRes = RunSim(1,1,'Case-Study') 

# Generate plot
fig,ax1 = plt.subplots(figsize=(10,6))
ax1.grid()
plt.title("Total annual generation (MPPT ) - Validation")
ax1.plot(dc['p_mp'],color='tab:blue',alpha=0.9)
# ax1.plot(dc[0]['p_mp'].resample('W').mean(),color='tab:blue',alpha=0.9)
ax1.set_xlabel('Date')
ax1.set_ylabel('Mean weekly PV power (W)',color='tab:blue')

ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
ax2.plot(np.cumsum(dc['p_mp']),color='tab:orange',alpha=0.9) # Can just sum rather than trapz cos 1H ints
ax2.set_ylabel('Total generation (Wh)',color='tab:orange')


# # Check case study energy in a certain month
# ---------------------
CSD = readCaseStudyData()

month = CSD.copy()
month = month["Solar Charger [289]_PV power_"].resample('H').mean()
month = month.loc['2024-03-01 00:00:00':'2024-03-31 23:00:00']

monthEnergy = np.sum(month)
print(monthEnergy)
# ---------------------

# Comparison between modelled and case study irradiance
modelled = Main.weatherData['ghi'].copy()
experimental = Main.CaseStudyData['Gateway [0]_Solar Irradiance_'].copy()

experimental = experimental[~experimental.index.duplicated(keep='first')]
experimental = experimental.apply(pd.to_numeric, errors='coerce')
experimental = experimental.dropna()
    
modelled.index = modelled.index.tz_convert(None)

startTime = experimental.index[0]
endTime = experimental.index[-1]

modelled = modelled.loc[startTime:endTime]

# Integrate using the trapezium rule
modelledSum = np.trapz(y=modelled)
experimentalSum = np.trapz(y=experimental)
percentDiff = (modelledSum-experimentalSum)/modelledSum * 100

print(['Modelled irradiance from ' + Main.weatherSource + '. Case study irradiance from Solcast. \n %Difference between Solcast and PVGIS = ' + str(percentDiff)] )


modelled = allRes.ac.loc['2021-07-01 00:00:00':'2021-07-31 23:00:00']
np.trapz(y=modelled)