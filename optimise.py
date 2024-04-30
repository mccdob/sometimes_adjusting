# -*- coding: utf-8 -*-
"""
Created on Thu Mar 14 15:39:13 2024

@author: miran
Optimisation script
"""

"""
Parameter space study for a given location
"""
import pandas as pd
import numpy as np
import pvlib
import scipy.stats as stats
import math

from RunSim import RunSim
import matplotlib.pyplot as plt

from matplotlib import cm
from matplotlib.ticker import LinearLocator
from pvlib import pvsystem

from pvlib.location import Location
from my_functions import generateWeather,averageConsumptionData

# Setup parameter space
facialityOpts = ["Monofacial","Bifacial"]
tiltOpts = np.arange(0,91,3)
aziOpts = np.arange(0,361,5)

# Initialise variables
EnergyResults = facialityOpts.copy()
tiltData = pd.DataFrame(columns=aziOpts)
EnergyResultsNet = facialityOpts.copy()
tiltDataNet = pd.DataFrame(columns=aziOpts)
wastedLocs = facialityOpts.copy()
wastedTilt = pd.DataFrame(columns=aziOpts)
selfCons = facialityOpts.copy()
selfConsPercent = facialityOpts.copy()
SelfConsumptionTilt = pd.DataFrame(columns=aziOpts)

x=0

# Set location
latitude = 56.82626812132033
longitude = -5.787276786944142
name = 'Case Study Site'

# Import weather data
site = Location(latitude=latitude, longitude=longitude, name=name) #UTC

season = "Year"   #Summer, Winter, Spring, Autumn, Year

if season == "Winter":
    start = '2021-01-01'
    end = '2021-02-28'
    levs = np.linspace(50,140,15)
    lab = 'Monthly generation over winter months (kWh)'
    factor = 2
elif season == "Summer":
    start = '2021-06-01'
    end = '2021-08-31'
else:
    season = "Year"
    start = '2021-01-01'
    end = '2021-12-31'
    levs = np.linspace(500,1950,20)
    lab = 'Yearly energy generation (kWh)'
    factor = 1

# Specify time model timeframe
times = pd.date_range(start, end, freq='1min',tz=site.tz)

# Specify weather source (model, database) 'clearSky','tmy','year'
year=times.year[0]
weatherSource = 'tmy'

# Generate and resample weather data to desired frequency
weatherData = generateWeather(weatherSource,site,times,year)
averageConsumptionData = averageConsumptionData(weatherData.index)

consumption = averageConsumptionData.loc[start:end][0]
consumptionTotal = sum(consumption)
weatherData = weatherData.loc[start:end]

# Generate module dbs
sandiaModules = pvlib.pvsystem.retrieve_sam('SandiaMod')
cecModules = pvlib.pvsystem.retrieve_sam(path = 'https://raw.githubusercontent.com/NREL/SAM/patch/deploy/libraries/CEC%20Modules.csv')
cecInverters = pvlib.pvsystem.retrieve_sam('CECInverter')


# Loop through variables
for faciality in facialityOpts:
    for tilt in tiltOpts:
        aziData = []
        aziDataNet = []
        wastedAzi = []
        SelfConsumption_total_azi=[]
        for azimuth in aziOpts:
            energy,dc,allRes = RunSim(tilt,azimuth,faciality,weatherData,site,
                                      sandiaModules,cecModules,cecInverters)
            net = allRes.ac-consumption[0]
            netEnergy_Int = sum(net)
            wastedAzi.append(sum(net.loc[net>0]))
            aziData.append(energy)
            aziDataNet.append(netEnergy_Int)
            
            # Self-consumption
            bools = allRes.ac>consumption
            yaboy = [consumption.iloc[i] if bools.iloc[i] else allRes.ac.iloc[i] for i in np.arange(len(bools))]
            SelfConsumption = pd.Series(data=yaboy, index=bools.index)
            SelfConsumption_total_azi.append(sum(SelfConsumption))
            
            # print(azimuth)
        tiltData.loc[tilt] = aziData
        tiltDataNet.loc[tilt] = aziDataNet
        wastedTilt.loc[tilt] = wastedAzi
        
        # Self-consumption
        SelfConsumptionTilt.loc[tilt] = SelfConsumption_total_azi

        print(tilt)
    EnergyResults[x] = tiltData.copy()
    EnergyResultsNet[x] = tiltDataNet.copy()
    wastedLocs[x] = wastedTilt.copy()
    selfCons[x] = SelfConsumptionTilt.copy()
    selfConsPercent[x] = selfCons[x]/consumptionTotal*100
    x=x+1


# # Plot surface
# fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
# plt.title('Year')
X = aziOpts
Y = tiltOpts
X, Y = np.meshgrid(X, Y)

# Plot total generation contour
fig4, ax4 = plt.subplots(ncols=2,nrows=1,figsize = (12,6),subplot_kw={"projection": "polar"})
fig4.suptitle(f"Parameter space study at {site.name} over a {season}, with {facialityOpts[0]} modules")
plotter = [EnergyResults[0], EnergyResultsNet[0]]
for i in range(2):
    Z = plotter[i]/(1000*factor)
    cs = ax4[i].contourf(np.deg2rad(X), Y, Z)
    # ax4[i].contour(np.deg2rad(X), Y, Z,colors="k",linewidths=0.5)

    ax4[i].set_theta_zero_location("N")
    ax4[i].set_theta_direction(-1)
    ax4[i].set_rlabel_position(88)
    ax4[i].text(np.deg2rad(135),10,'Tilt (degs from horizontal)',rotation = 1)
    ax4[i].set_xlabel('Azimuth (degrees from North)')
    plt.colorbar(cs,label=lab, ax=ax4[i])

ax4[0].set_title("Total generation")
ax4[1].set_title("Net generation")
fig4.tight_layout()
plt.show()

#PLot absolute self consumption contours
fig5, ax5 = plt.subplots(ncols=2,nrows=1,figsize = (12,6),subplot_kw={"projection": "polar"})
fig5.suptitle(f"Parameter space study at {site.name} over a {season}")
for i in range(len(EnergyResults)):
    Z = selfCons[i]/(1000*factor)
    cs = ax5[i].contourf(np.deg2rad(X), Y, Z,levels=50)
    csLab=ax5[i].contour(np.deg2rad(X), Y, Z,colors="k",linewidths=0.5)
    ax5[i].set_title(facialityOpts[i])
    ax5[i].set_theta_zero_location("N")
    ax5[i].set_theta_direction(-1)
    ax5[i].set_yticklabels([])    
    plt.colorbar(cs,label="Self-consumption (kWh)", ax=ax5[i])
    ax5[i].clabel(csLab,csLab.levels,inline=True)
    ax5[i].set_xlabel('Azimuth (degrees from North)')
    
fig5.tight_layout()
plt.show()

# Plot selfconsumption as a percentage contours
fig5, ax5 = plt.subplots(ncols=2,nrows=1,figsize = (12,6),subplot_kw={"projection": "polar"})
fig5.suptitle(f"Parameter space study at {site.name} over a {season}")
for i in range(len(EnergyResults)):
    Z = selfConsPercent[i]
    cs = ax5[i].contourf(np.deg2rad(X), Y, Z,levels=50)
    csLab=ax5[i].contour(np.deg2rad(X), Y, Z,colors="k",linewidths=0.5)
    ax5[i].set_title(facialityOpts[i])
    ax5[i].set_theta_zero_location("N")
    ax5[i].set_theta_direction(-1)
    ax5[i].set_yticklabels([])
    plt.colorbar(cs,label="Self-consumption (%)", ax=ax5[i])
    ax5[i].clabel(csLab,csLab.levels,inline=True)
    ax5[i].set_xlabel('Azimuth (degrees from North)')

fig5.tight_layout()
plt.show()
