"""
Created on Mon Mar 25 16:50:00 2024

@author: miran

Finding trends in variation of tilt with latitude
"""

import scipy.optimize as spo
import pandas as pd
import numpy as np
import pvlib
import csv

from statistics import mean 
import scipy.stats as stats

from RunSim import RunSim
import matplotlib.pyplot as plt

from pvlib.location import Location
from my_functions import generateWeather,averageConsumptionData

import warnings

# supressing shapely warnings that occur on import of pvfactors
warnings.filterwarnings(action='ignore', module='pvfactors')

# Set up user inputs
season = "Year"   #Summer, Winter, Spring, Autumn, Year
faciality = 'Monofacial'
# Import weather data to speed up sim.
if season == "Winter":
    start = '2021-01-01'
    end = '2021-02-28'
    db=15
elif season == "Summer":
    start = '2021-06-01'
    end = '2021-08-31'
    db=-15
else:
    season = "Year"
    start = '2021-01-01'
    end = '2021-12-31'
    db=0
    
# Specify/import test locations
df = pd.read_csv('G:\My Drive/Uni stuff/WOrk/Notability (Y1-3)/Y4S2/FYP/Reporting/locations2.csv', encoding='latin-1')
testSites = []
for i in range(len(df)):
    site = Location(df['latitude'][i],df['longitude'][i],name =df['NOM'][i])
    testSites.append(site)

times = pd.date_range(start, end, freq='1min')
year=times.year[0]

sandiaModules = pvlib.pvsystem.retrieve_sam('SandiaMod')
cecModules = pvlib.pvsystem.retrieve_sam(path = 'https://raw.githubusercontent.com/NREL/SAM/patch/deploy/libraries/CEC%20Modules.csv')
cecInverters = pvlib.pvsystem.retrieve_sam('CECInverter')
weatherSource = 'tmy'
resultSites = []
tempSites = []
irradSites = []
# 


# Loop through locations, finding the optimal orientation at each.
for s in range(len(testSites)):
    print(testSites[s].name)
    args = []
    args.append(faciality) # 0
    args.append(sandiaModules) # 1
    args.append(cecModules) # 2
    args.append(cecInverters) # 3
    
    weatherData = generateWeather(weatherSource,testSites[s],times,year)
    ConsumptionData = averageConsumptionData(weatherData.index)
    
    consumption = ConsumptionData.loc[start:end][0]
    weatherData = weatherData.loc[start:end]
    
    args.append(weatherData) # 4
    args.append(testSites[s]) # 5
    args.append(consumption) # 6
    
    # Define the objective function, which returns the optimisation metric
    def objFGeneration(variables,args):
        """objective function, to be solved."""
        # Unpack tuples
        tilt,azimuth = variables[0],variables[1]
        faciality,weatherData,site,sandiaModules,cecModules,cecInverters = args[0],args[4],args[5],args[1],args[2],args[3]
        
        # Run sim
        energy,dc,allRes = RunSim(tilt,azimuth,faciality,weatherData,site,
                              sandiaModules,cecModules,cecInverters)
        consumption = args[6]
        bools = allRes.ac>consumption
        yaboy = [consumption.iloc[i] if bools.iloc[i] else allRes.ac.iloc[i] for i in np.arange(len(bools))]
        SelfConsumption = pd.Series(data=yaboy, index=bools.index)
        
        SelfConsumption_total = sum(SelfConsumption)
        # print(tilt,azimuth,SelfConsumption_total)
        return -SelfConsumption_total
    
    initial_guess = [0,180]  # initial guess can be anything
    bnds = ((0,90),(0,360))
    #Run optimiser function
    result = spo.minimize(objFGeneration, initial_guess,args,bounds = bnds)
    print(f"For a {args[0]} array over {season}:\n Total self consumption of {abs(result.fun)} from Optimal tilt = {result.x[0]}, Optimal azimuth = {result.x[1]}")     
    resultSites.append(result)

    # Cell temp and irradiation investigation
    energy,dc,allRes = RunSim(result.x[0],result.x[1],faciality,weatherData,site,sandiaModules,cecModules,cecInverters)
    solNoon = weatherData['apparent_zenith'].idxmin().hour
    solMidnight = weatherData['apparent_zenith'].idxmax().hour
    meanNet = []
    netIrrad = []
    for x in range(max(allRes.cell_temperature.index.dayofyear)):
        dailyCellTemp = allRes.cell_temperature[allRes.cell_temperature.index.dayofyear==x+1]
        dailyCellTemp.index = dailyCellTemp.index.hour
        dailyCellTemp = dailyCellTemp.dropna()        
        mean1 = mean(dailyCellTemp[(dailyCellTemp.index < solNoon) | (dailyCellTemp.index > solMidnight)])
        mean2 = mean(dailyCellTemp[(dailyCellTemp.index > solNoon) | (dailyCellTemp.index < solMidnight)])
        meanNet.append(mean1-mean2)
        
        dailyIrrad = weatherData[weatherData.index.dayofyear==x+1]['ghi']
        dailyIrrad.index = dailyIrrad.index.hour
        morningIrrad = sum(dailyIrrad[(dailyIrrad.index < solNoon) | (dailyIrrad.index > solMidnight)])
        afternoonIrrad = sum(dailyIrrad[(dailyIrrad.index > solNoon) | (dailyIrrad.index < solMidnight)])
        netIrrad.append(morningIrrad-afternoonIrrad)
        
    tempSites.append(mean(meanNet)) 
    irradSites.append(mean(netIrrad))

print(resultSites)


#Plot results
fig,ax = plt.subplots(ncols=1,nrows=2,figsize = (10,6),sharex=True)
# ax[0].title.set_text(f'Effect of latitude on optimal orientation ({season}, {faciality})')
X=np.empty(shape=(len(testSites)))
Y1=np.empty(shape=(len(testSites)))
Y2=np.empty(shape=(len(testSites)))
for x in range(len(resultSites)):
    X[x] = testSites[x].latitude
    Y1[x] = resultSites[x].x[0]
    Y2[x] = resultSites[x].x[1]
    ax[0].plot(X[x],Y1[x],'x')
    ax[1].plot(X[x],Y2[x],'x')
    # Write to csv
    with open("G:\My Drive/Uni stuff/WOrk/Notability (Y1-3)/Y4S2/FYP/Reporting/results/eggs.csv", 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([testSites[x].name, testSites[x].latitude, testSites[x].longitude, resultSites[x].fun, resultSites[x].x[0], resultSites[x].x[1]])

orientation = pd.DataFrame({'Tilt':Y1, 'Azimuth':Y2}, index=X)
orientation = orientation.sort_index()

#Trend lines
#Tilt
#DuffieBeckman
# ax[0].plot(X,X+db,label=f'DuffieBeckman, y=x+{db}',color='tab:red',linewidth=0.5)
# ax[0].plot(X,-(X+db),color='tab:red',linewidth=0.5)
# ax[0].axvline(0,color="black", linestyle="--",linewidth=0.5)
# ax[0].text(0.5,3,'Equator',rotation=90)
#Quadratic
notfailed = orientation[np.invert((orientation['Tilt']==90) | (orientation['Tilt']==0))]
fit = np.polyfit(notfailed.index[notfailed.index>0], notfailed[notfailed.index>0]['Tilt'], 1, full=True)
ax[0].plot(notfailed.index[notfailed.index>0], np.polyval(fit[0],notfailed.index[notfailed.index>0]),label="Fit line (linear)")
fit2 = np.polyfit(notfailed.index[notfailed.index>0], notfailed[notfailed.index>0]['Tilt'], 2, full=True)
ax[0].plot(notfailed.index[notfailed.index>0], np.polyval(fit2[0],notfailed.index[notfailed.index>0]),label="Fit line (quadratic)")
# ax[0].legend()

#Azimuth
fitt2 = np.polyfit(notfailed.index[notfailed.index>0], notfailed[notfailed.index>0]['Azimuth'], 1, full=True)
ax[1].plot(notfailed.index[notfailed.index>0], np.polyval(fitt2[0],notfailed.index[notfailed.index>0] ),label='Fit line (linear)')
# ax[1].legend()

# plt.title('Effect of latitude     on optimal orientation')
ax[1].set_xlabel('Latitude')
ax[1].axhline(180,color="black", linestyle="--",linewidth=0.5)
ax[1].text(60,182,'South',rotation=0)
ax[1].axhline(90,color="black", linestyle="--",linewidth=0.5)
ax[1].text(60,92,'East',rotation=0)
ax[1].axhline(270,color="black", linestyle="--",linewidth=0.5)
ax[1].text(60,272,'West',rotation=0)
ax[1].axvline(0,color="black", linestyle="--",linewidth=0.5)
ax[1].text(0.5,10,'Equator',rotation=90)

ax[0].set_ylabel('Optimal tilt angle (degrees)')
ax[1].set_ylabel('Optimal azimuth angle (degrees)')

ax[0].set_ylim(0,90)
ax[1].set_ylim(0,360)
fig.suptitle(f'Effect of latitude on optimal orientation ({season}, {faciality})')
fig.tight_layout()

# PLot 177 investigation results
# fig2,ax2 = plt.subplots(ncols=1,nrows=2,figsize=(10,6),sharex=True)
# for x in range(len(resultSites)):
#     ax2[1].plot(testSites[x].latitude,tempSites[x],'x')
#     ax2[0].plot(testSites[x].latitude,irradSites[x],'x')
# # areaNet=[]
# # area1=0
# # area2=0
# # for j in range(len(Irrad)):
# #     for x in range(max(Irrad[j].index.dayofyear)):
# #         dailyIrrad = Irrad[j][Irrad[j].index.dayofyear==x+1]
# #         dailyIrrad.index = dailyIrrad.index.hour

# #         area1=area1+sum(dailyIrrad[(dailyIrrad.index < solNoon) | (dailyIrrad.index > solMidnight)])
# #         area2=area2+sum(dailyIrrad[(dailyIrrad.index > solNoon) | (dailyIrrad.index < solMidnight)])

# #     areaNet.append(area1-area2)
# #     ax2[0].plot(testSites[j].latitude,area1-area2,'x')
    
# ax2[1].set_xlabel('Latitude')
# ax2[1].axvline(0,color="black", linestyle="--",linewidth=0.5)
# ax2[1].text(0.5,0,'Equator',rotation=90)
# ax2[1].axhline(0,color="black", linestyle="--",linewidth=0.5)
# ax2[0].axhline(0,color="black", linestyle="--",linewidth=0.5)
# ax2[0].axvline(0,color="black", linestyle="--",linewidth=0.5)
# ax2[0].text(0.5,0,'Equator',rotation=90)
# ax2[0].set_ylabel('Net Irradiation (Wh/m^2)')
# ax2[1].set_ylabel('Net temperature (deg C)')

# ax2[0].set_title('Net daily irradiation (Morning-Afternoon)')
# ax2[1].set_title('Net daily mean temperature (Morning-Afternoon)')
# fig2.suptitle(f"{season}, {faciality}")
# fig2.tight_layout()


# Hypothesis testing.

# fig3,ax3 = plt.subplots(figsize =(10,6))
# plt.hist(orientation['Azimuth'],)
s = orientation.loc[notfailed.index]
# plt.hist(s['Azimuth'])
# plt.hist(s[s.index>0]['Azimuth'])
northernLats1 = stats.ttest_1samp(a = s['Azimuth'], popmean = 180)
allLats1 = stats.ttest_1samp(a = s[s.index>0]['Azimuth'], popmean = 180)
northernLats2 = stats.ttest_1samp(a = orientation['Azimuth'], popmean = 180)
allLats2 = stats.ttest_1samp(a = orientation[orientation.index>0]['Azimuth'], popmean = 180)

x = notfailed.index[notfailed.index>0]
y = notfailed[notfailed.index>0]['Tilt']
print(stats.linregress(x,y))
y = notfailed[notfailed.index>0]['Azimuth']
print(stats.linregress(x,y))