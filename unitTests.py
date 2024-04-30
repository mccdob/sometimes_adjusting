# -*- coding: utf-8 -*-
"""
Created on Mon Apr 22 09:40:11 2024

@author: miran
"""

import unittest

import pvlib
import pandas as pd
import numpy as np
from RunSim import RunSim
from pvlib.location import Location
from my_functions import generateWeather, averageConsumptionData
import matplotlib.pyplot as plt

import warnings

# supressing shapely warnings that occur on import of pvfactors
warnings.filterwarnings(action='ignore', module='pvfactors')

# All tests run at the case study location
# Set up user inputs
latitude = 56.82626812132033
longitude = -5.787276786944142
faciality="Monofacial"
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

# Set up demand and weather data
year=times.year[0]
weatherSource = 'tmy'
weatherData = generateWeather(weatherSource,site,times,year)
averageConsumptionData = averageConsumptionData(weatherData.index)

#IMport modules and inverters
sandiaModules = pvlib.pvsystem.retrieve_sam('SandiaMod')
cecModules = pvlib.pvsystem.retrieve_sam(path = 'https://raw.githubusercontent.com/NREL/SAM/patch/deploy/libraries/CEC%20Modules.csv')
cecInverters = pvlib.pvsystem.retrieve_sam('CECInverter')

consumption = averageConsumptionData.loc[start:end][0]
weatherData = weatherData.loc[start:end]

# Run verification tests
class TestStringMethods(unittest.TestCase):

    # Test generation is consistent for all azimuths when tilt=0
    def test_horizontal(self):
        tilt=0
        aziData=[]
        aziOpts = np.linspace(0,360,2)
        for azimuth in aziOpts:
            energy,dc,allRes = RunSim(tilt,azimuth,faciality,weatherData,site,
                                      sandiaModules,cecModules,cecInverters)

            aziData.append(energy)
            
        for i in range(0,len(aziOpts)-1):
            with self.subTest(i=i):
                self.assertAlmostEqual(aziData[i], aziData[i+1])


    # Test gen monofacial=bifacial with bifaciality=0
    # This test fails - showing bifacial and monofacial results are not comparable
    def test_bifacial(self):
        tilt = 35
        azimuth = 185
        energyMono,dc,allRes = RunSim(tilt,azimuth,"Monofacial",weatherData,site,
                                      sandiaModules,cecModules,cecInverters)
        energyBi0,dc,allRes = RunSim(tilt,azimuth,"Bifacial",weatherData,site,
                                      sandiaModules,cecModules,cecInverters,
                                      bifaciality=0)
        self.assertAlmostEqual(energyMono,energyBi0,0)


    # Test demand=0, self consumption=0
    def test_selfConsumption(self):
        tilt = 35
        azimuth = 185
        energy,dc,allRes = RunSim(tilt,azimuth,faciality,weatherData,site,
                              sandiaModules,cecModules,cecInverters)
        consumption[:] = 0
        bools = allRes.ac>consumption
        allRes.ac[allRes.ac < 0] = 0
        yaboy = [consumption.iloc[i] if bools.iloc[i] else allRes.ac.iloc[i] for i in np.arange(len(bools))]
        SelfConsumption = pd.Series(data=yaboy, index=bools.index)
        
        SelfConsumption_total = sum(SelfConsumption)
        
        self.assertEqual(SelfConsumption_total, 0)
        
        
    # Test no irradiance in, generation=0
    def test_zeroIrradiance(self):
        tilt = 35
        azimuth = 185
        weatherData["ghi"] = 0
        weatherData["dni"] = 0
        weatherData["dhi"] = 0
        energy,dc,allRes = RunSim(tilt,azimuth,faciality,weatherData,site,
                              sandiaModules,cecModules,cecInverters)
        
        self.assertEqual(energy, 0)

        
    # Test nominal clearsky generation
    def test_nominalClearSky(self):
        tilt = 34.3
        azimuth = 180
        start = '2021-06-01'
        end = '2021-06-30'
        times = pd.date_range(start, end, freq='1min',tz=site.tz)
        weatherSource = 'clearSky'
        weatherData = generateWeather(weatherSource,site,times,year)
        
        # Scale weather data
        ghi = (weatherData["ghi"] - weatherData["ghi"].min()) / (weatherData["ghi"].max() - weatherData["ghi"].min())
        ghi[:]=ghi*1000
        
        energy,dc,allRes = RunSim(tilt,azimuth,faciality,weatherData,site,
                              sandiaModules,cecModules,cecInverters)
        
        # Check within 15%
        bound=1.15
        lower = 1750/bound
        upper = 1750*bound
        self.assertGreater(dc["p_mp"].max(), lower)
        self.assertLess(dc["p_mp"].max(), upper)
        
        fig,ax=plt.subplots()
        ax.plot(ghi,alpha=0.5)
        ax.plot(dc["p_mp"],alpha=0.5)
        
        
if __name__ == '__main__':
    unittest.main()