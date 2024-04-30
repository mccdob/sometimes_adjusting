# -*- coding: utf-8 -*-
"""
Created on Wed Mar 20 10:41:10 2024

@author: miran
"""

import scipy.optimize as spo
import pandas as pd
import numpy as np
import pvlib

from RunSim import RunSim
import matplotlib.pyplot as plt

from pvlib.location import Location
from my_functions import generateWeather, averageConsumptionData

import warnings

# supressing shapely warnings that occur on import of pvfactors
warnings.filterwarnings(action='ignore', module='pvfactors')

# Set up user inputs
latitude = 56.82626812132033
longitude = -5.787276786944142
season = "Year"   #Summer, Winter, Spring, Autumn, Year

# Import weather data to speed up sim.
if season == "Winter":
    start = '2021-01-01'
    end = '2021-02-28'
elif season == "Summer":
    start = '2021-06-01'
    end = '2021-08-31'
else:
    season = "Year"
    start = '2021-01-01'
    end = '2021-12-31'

site = Location(latitude=latitude, longitude=longitude, name='Case Study Site') #UTC
times = pd.date_range(start, end, freq='1min',tz=site.tz)
year=times.year[0]
weatherSource = 'tmy'
weatherData = generateWeather(weatherSource,site,times,year)
averageConsumptionData = averageConsumptionData(weatherData.index)

sandiaModules = pvlib.pvsystem.retrieve_sam('SandiaMod')
cecModules = pvlib.pvsystem.retrieve_sam(path = 'https://raw.githubusercontent.com/NREL/SAM/patch/deploy/libraries/CEC%20Modules.csv')
cecInverters = pvlib.pvsystem.retrieve_sam('CECInverter')

consumption = averageConsumptionData.loc[start:end][0]
weatherData = weatherData.loc[start:end]

args = []
args.append('Bifacial')
args.append(weatherData)
args.append(site)
args.append(sandiaModules)
args.append(cecModules)
args.append(cecInverters)
args.append(consumption)

# Genreate objective function for optimiser. Function returns total generation
def objFGeneration(variables,args):
    """objective function, to be solved."""
    # Unpack tuples
    tilt,azimuth = variables[0],variables[1]    
    faciality,weatherData,site,sandiaModules,cecModules,cecInverters = args[0],args[1],args[2],args[3],args[4],args[5]
    
    # Run sim
    energy,dc,allRes = RunSim(tilt,azimuth,faciality,weatherData,site,
                          sandiaModules,cecModules,cecInverters)
    print(tilt,azimuth,energy)
    return -energy

initial_guess = [60,180]  # initial guess can be anything
bnds = ((0,90),(0,360))


###########
    # Create object to store optimisation results
class OptimizationData:
    def __init__(self):
        self.iter_values = []
    
    def record_iteration(self, energy):
        self.iter_values.append(energy)
            
ntests=100
fig,ax = plt.subplots(figsize=(10,6))
for test in range(ntests):
    ti = np.random.uniform(0,90)
    az = np.random.uniform(0,360)
    initial_guess = [ti,az] 
    # Create an instance of OptimizationData
    optimizer_data = OptimizationData()
    
    # Define a callback function to record iteration results
    def callback_function(variables):
        tilt, azimuth = variables
        energy = -objFGeneration(variables, args)
        optimizer_data.record_iteration(energy)
    
    # Perform unconstrained optimization
    result = spo.minimize(
        objFGeneration,
        initial_guess,
        args=args,
        bounds=bnds,
        method='L-BFGS-B',  # Example method (you can choose other methods)
        callback=callback_function
    )
    
    # Plot convergence behavior
    ax.plot(optimizer_data.iter_values, label=f'Test {test + 1}, Initial guess = ({initial_guess[0]:.1f},{initial_guess[1]:.1f})')
ax.set_xlabel('Iteration')
ax.set_ylabel('Objective Function Value (Total generation, Wh)')
# ax.legend()
plt.title('Convergence Plot')
plt.show()

# Print optimized tilt and azimuth
print("Optimized Tilt:", result.x[0])
print("Optimized Azimuth:", result.x[1])
print("Optimized Energy:", -result.fun)  # Minimize -energy to maximize energy



def objFNetEnergy(variables,args):
    """objective function, to be solved."""
    # Unpack tuples
    tilt,azimuth = variables[0],variables[1]
    faciality,weatherData,site,sandiaModules,cecModules,cecInverters = args[0],args[1],args[2],args[3],args[4],args[5]
    
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

bnds = ((0,90),(0,360))
initial_guess = [45,180]  # initial guess can be anything
result = spo.minimize(objFNetEnergy, initial_guess,args
                        ,bounds = bnds
                      )
print(f"For a {args[0]} array over {season}:\n Total self consumption of {abs(result.fun)} from Optimal tilt = {result.x[0]}, Optimal azimuth = {result.x[1]}")