# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 12:48:13 2024

@author: miran

Function for runnign simulations
"""

# Import libraries
from pvlib.location import Location
import pandas as pd
import numpy as np
from pvlib.modelchain import ModelChain

# Import my functions
from my_functions import CaseStudyMPVChain,generateWeather

#Create function for building and running the mdoelchain
def RunSim(tilt,azimuth,faciality,weatherData=None,
           site=Location(latitude=56.82626812132033, longitude=-5.787276786944142, name='Case Study Site'),
           sandiaModules=None,cecModules=None,cecInverters=None,bifaciality=0.95):
    
    #Create weather data
    if weatherData is None:
        site = Location(latitude=56.82626812132033, longitude=-5.787276786944142, name='Case Study Site') #UTC
        
        # Specify time model timeframe
        times = pd.date_range(start='2023-01-01', end='2023-12-31', freq='1min',tz=site.tz)
        
        # Specify weather source (model, database) 'clearSky','tmy','year'
        year=times.year[0]
        weatherSource = 'clearSky'
        
        # Generate and resample weather data to desired frequency
        weatherData = generateWeather(weatherSource,site,times,year)
   
    # Generate PV system model (Module, Inverter, layout)
    # Panels can be 'Case-Study', 'Bifacial', or maybe something else
    system,irrad = CaseStudyMPVChain(weatherData,faciality,tilt,azimuth,sandiaModules,cecModules,cecInverters,bifaciality)
    
    # Generate model chain (Modelchain automates certain aspects of the model chain)
    modelchain = ModelChain(system, site, aoi_model='no_loss',spectral_model="no_loss")

    # Run model chain and generate results
    modelchain.run_model(weatherData)
    mcAllResults = modelchain.results
    
    dcResults = modelchain.results.dc
    
    # Different solver used for bifacial panels
    if faciality == 'Bifacial':
        modelchain.run_model_from_effective_irradiance(irrad)
        mcAllResults = modelchain.results
        dcResults = modelchain.results.dc
        
        
    # Integrate power over the year to gather the total energy generation.
    EnergyGen = np.trapz(y=dcResults['p_mp'])
    return EnergyGen, dcResults, mcAllResults

if __name__ == '__main__':
    energy,dc,mcAllResults = RunSim(35,180,'Monofacial')
