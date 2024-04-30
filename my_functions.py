# -*- coding: utf-8 -*-
"""
Created on Tue Feb 20 18:16:41 2024

@author: miran
"""

import pvlib
import pandas as pd
import datetime
import matplotlib.pyplot as plt

from pvlib.bifacial.pvfactors import pvfactors_timeseries

from pvlib.pvsystem import PVSystem, Array, FixedMount
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS

def ImportPVGISData(site,times,year='tmy'):
    '''
    Import data from the PVGIS databases

    '''
    if year =='tmy':
        poaData, months, inputs, meta = pvlib.iotools.get_pvgis_tmy(
            latitude = site.latitude, 
            longitude= site.longitude,
            outputformat='json', 
            usehorizon=True, 
            userhorizon=None,
            url= 'https://re.jrc.ec.europa.eu/api/v5_2/', 
            map_variables=True, 
            timeout=120
            )

        #
        if times.year[0]==times.year[-1]:
            poaData.index = pd.date_range("2021-01-01 00:00","2021-12-31 23:00",freq="h",tz=site.tz)
        else:
            # Create index with months in correct order
            if times.year[0]==2024:
                end1 = datetime.datetime(times.year[0],12,30,23) 
            else:
                end1 = datetime.datetime(times.year[0],12,31,23)
            start1 = datetime.datetime(times.year[0],1,1,0)
            df1 = poaData.copy()
            df1.index = pd.date_range(start1,end1,freq="h",tz=site.tz)
            if times.year[-1]==2024:
                end2 = datetime.datetime(times.year[-1],12,30,23) 
            else:
                end2 = datetime.datetime(times.year[-1],12,31,23)
            start2 = datetime.datetime(times.year[-1],1,1,0)
            df2 = poaData.copy()
            df2.index = pd.date_range(start2,end2,freq="h",tz=site.tz)
    
            #Create new df with index range as specificed
            df1 = df1.loc[times[0]:]
            df2 = df2.loc[:times[-1]]
            poaData = pd.concat([df1,df2])


    else:
        poaData, meta, inputs = pvlib.iotools.get_pvgis_hourly(
            latitude = site.latitude, 
            longitude= site.longitude,
            # start = year, 
            # end= year, 
            raddatabase="PVGIS-SARAH2", 
            components=True,
            surface_tilt=0, 
            surface_azimuth=180, 
            outputformat='json', 
            usehorizon=True, 
            userhorizon=None, 
            pvcalculation=False, 
            peakpower=None,
            pvtechchoice='crystSi', 
            mountingplace='free', 
            loss=0, 
            trackingtype=0, 
            optimal_surface_tilt=False, 
            optimalangles=False, 
            url='https://re.jrc.ec.europa.eu/api/v5_2/', 
            map_variables=True, 
            timeout=30
            )
    
        poaData['dhi'] = poaData['poa_sky_diffuse'] + poaData['poa_ground_diffuse']
        poaData['ghi'] = poaData['dhi'] + poaData['poa_direct']
        poaData['dni'] = poaData['poa_direct']
    
    return poaData

#---------------------------------------------------------------------------------
def generateWeather(weatherSource,site,times,year):
    # Generate weatehr data from the PVGIS database
    if weatherSource == 'clearSky':
        print('Clear sky model used to generate weather data')
        weatherData = site.get_clearsky(times)
        
    elif weatherSource == 'tmy':
        # print('Typical Metrological Year weather data used')
        weatherData = ImportPVGISData(site,times,year='tmy')
        times = weatherData.index

    else:
        print(f"Weather data for the year {year} used")
        weatherData = ImportPVGISData(site,times,year)
        
    # Insert solar positions into the weatehr data dataframe for bifacial modelling
    solar_position = site.get_solarposition(times)
    weatherData.insert(len(weatherData.columns),'apparent_zenith',solar_position['apparent_zenith'])
    weatherData.insert(len(weatherData.columns),'azimuth',solar_position['azimuth'])
    
    return weatherData

#---------------------------------------------------------------------------------
def CaseStudyMPVChain(poaData,panels,tilt,azimuth,sandiaModules=None,cecModules=None,cecInverters=None,bifaciality=0.95):
    """
    Case study system modelchain setup
    """
    
    # Retrieve system components
    if sandiaModules is None:
        sandiaModules = pvlib.pvsystem.retrieve_sam('SandiaMod')
    if cecModules is None:
        cecModules = pvlib.pvsystem.retrieve_sam(path = 'https://raw.githubusercontent.com/NREL/SAM/patch/deploy/libraries/CEC%20Modules.csv')
    if cecInverters is None:
        cecInverters = pvlib.pvsystem.retrieve_sam('CECInverter')
    
    # Select temperature model
    temperatureParameters = TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']

    irrad = None
    
    if panels == 'Case-Study':
        # Select system components
        PERCmodule = cecModules['JA_Solar_JAM54S30_415_MR']
        module = cecModules['Merlin_Solar_Technologies_Inc__RFP_F036W175S']
        inverter = cecInverters['OutBack_Power_Technologies___Inc___GS4048A__240V_']
        
        # Defining multiple arrays - arrays of interest can be commented in/out as needed
        arrays = [
            Array(FixedMount(surface_tilt=60,surface_azimuth=180),
                    name="MPPT-289",
                    module_parameters=module,
                    temperature_model_parameters = temperatureParameters,
                    modules_per_string=5,
                    strings = 2)
            # ,
            # Array(FixedMount(surface_tilt=30,surface_azimuth=180),
            #         name="MPPT-274",
            #         module_parameters=module,
            #         temperature_model_parameters = temperatureParameters,
            #         modules_per_string=5,
            #         strings = 2)
            # ,
            # Array(FixedMount(surface_tilt=30,surface_azimuth=158),
            #         name="MPPT-291",
            #         module_parameters=PERCmodule,
            #         temperature_model_parameters = temperatureParameters,
            #         modules_per_string=2,
            #         strings = 4)
            ]
        
    elif panels == 'Bifacial':
                
        # Select system components
        module = cecModules['Merlin_Solar_Technologies_Inc__RFP_F036W175S']
        inverter = cecInverters['OutBack_Power_Technologies___Inc___GS4048A__240V_']
        
        # Define array
        arrays = [
            Array(FixedMount(surface_tilt=tilt,surface_azimuth=azimuth),
                    name="BiArray",
                    module_parameters=module,
                    temperature_model_parameters = temperatureParameters,
                    modules_per_string=5,
                    strings = 2)
        ]
        
        # Define bifacial parameters
        gcr = 0.1
        albedo = 0.3
        axis_azimuth = azimuth+90
        
        # Generate irradiation timeseries using pvfactors
        irrad = pvfactors_timeseries(poaData['azimuth'],
                                     poaData['apparent_zenith'],
                                     azimuth,
                                     tilt,
                                     axis_azimuth, # because fixed tilt
                                     poaData.index,
                                     poaData['dni'],
                                     poaData['dhi'],
                                     gcr,
                                     pvrow_height = 1,
                                     pvrow_width = 1,
                                     albedo=albedo
                                     )
        
        # turn into pandas DataFrame
        irrad = pd.concat(irrad, axis=1)
        
        # create bifacial effective irradiance using aoi-corrected timeseries values
        irrad['effective_irradiance'] = (
            irrad['total_abs_front'] + (irrad['total_abs_back'] * bifaciality)
        )
        
        
    elif panels == 'Monofacial':
        
        # Select system components
        module = cecModules['Merlin_Solar_Technologies_Inc__RFP_F036W175S']
        inverter = cecInverters['OutBack_Power_Technologies___Inc___GS4048A__240V_']
        
        # Define array
        arrays = [
            Array(FixedMount(surface_tilt=tilt,surface_azimuth=azimuth),
                    name="MonoArray",
                    module_parameters=module,
                    temperature_model_parameters = temperatureParameters,
                    modules_per_string=5,
                    strings = 2)
        ]
        
    elif panels == 'PERC_Rom':
    
        # Select system components
        PERCmodule = cecModules['JA_Solar_JAM60S10_330_PR']
        inverter = cecInverters['OutBack_Power_Technologies___Inc___GS4048A__240V_']
        
        # Define array
        arrays = [
            Array(FixedMount(surface_tilt=25,surface_azimuth=180),
                    name="PERCArray_Rom",
                    module_parameters=PERCmodule,
                    temperature_model_parameters = temperatureParameters,
                    modules_per_string=4,
                    strings = 2)
        ]
        
    elif panels == 'Mono_Rom':
    
        # Select system components
        module = cecModules['United_Renewable_Energy_Co__Ltd__D7K360H8A']
        inverter = cecInverters['OutBack_Power_Technologies___Inc___GS4048A__240V_']
        
        # Define array
        arrays = [
            Array(FixedMount(surface_tilt=25,surface_azimuth=180),
                    name="MonoArray_Rom",
                    module_parameters=module,
                    temperature_model_parameters = temperatureParameters,
                    modules_per_string=4,
                    strings = 2)
        ]
    else:
        print("No panel system information found")

    system = PVSystem(arrays = arrays, 
                      inverter_parameters=inverter,
                      temperature_model_parameters=temperatureParameters)
 
    # Return dict containing information about the model
    return system,irrad

#---------------------------------------------------------------------------
def readCaseStudyData():
    
    fileName = ["0_Multiplus485000GX_log_20230820-1648_to_20231019-1648",
                "0_Multiplus485000GX_log_20231019-1648_to_20231218-1548",
                "0_Multiplus485000GX_log_20231218-1548_to_20240216-1548",
                "0_Multiplus485000GX_log_20240216-1548_to_20240220-1547"]
    rt = r"G:\My Drive\Uni stuff\WOrk\Notability (Y1-3)\Y4S2\FYP\Modelling\Andrews panels\\"
    end = ".csv"
    
    header_rows = pd.read_csv(rt+fileName[1]+end, index_col=0,nrows=3, header=None)
    header_rows.fillna('', inplace=True)
    combined_header = header_rows.iloc[0] + '_' + header_rows.iloc[1] + '_' + header_rows.iloc[2]
    
    # Create empty dataframe
    CaseStudyData = pd.DataFrame()
    for x in fileName:
        print(x)
        # Read csv, skip rows, combine first 3 rows to a single headogn
        toAppend = pd.read_csv(rt+x+end,index_col=0, skiprows=3,header=None)
        CaseStudyData = pd.concat([CaseStudyData,toAppend])

    CaseStudyData.columns = combined_header
    CaseStudyData.index = pd.to_datetime(CaseStudyData.index)
    return CaseStudyData

def averageConsumptionData(times):
    # Average consumption data exptracted form plot in report.
    summer = [322.9741931,286.7924528,284.2767296,249.0566038,
              251.572327,236,221.3836478,314.4654088,437.7358491,
              447.7987421,430.1886792,442.7672956,455.3459119,
              394.9685535,379.8742138,407.5471698,440.2515723,
              500.6289308,533.3333333,538.3647799,535.8490566,
              525.7,515.7232704,454.6504296
              ]
    winter = [682.8230953,561.0062893,387.4213836,334.591195,
              364.7798742,374.3,384.0826487,493.081761,
              679.245283,681.7610063,727.0440252,711.9496855,
              729.5597484,759.7484277,769.8113208,767.2955975,
              880.5031447,1091.823899,1122.012579,1081,
              1041.509434,996.2264151,903.1446541,832.7044025
              ]
    average = [460.7151931,308.1419624,265.5532359,240.5010438,
               263.0480167,245.5114823,270.5636743,375.782881,
               503.5490605,508.559499,503.5490605,483.5073069,
               503.5490605,483.5073069,458.4551148,481.0020877,
               546.1377871,648.8517745,731.5240084,722.7,
               713.9874739,681.4196242,611.2734864,558.6638831
               ]

    year = winter*(28+31)
    year.extend(average*(31*2+30))
    year.extend(summer*(31*2+30))
    year.extend(average*(30*2+31))
    year.extend(winter*31)
    
    consumptionData = pd.DataFrame(year,times)
    return consumptionData
#-------------------------------------------------------------------------------
def plotCaseStudyData(CaseStudyData,weatherData):    
    figRt = "../../Reporting/pyplots/"
    figName = "Solar charger properties"
    fig,ax1 = plt.subplots(figsize=(10,6))
    plt.title("Solar charger properties")
    
    # plotCols = ["Solar Charger [289]_PV power_","Solar Charger [274]_PV power_"]
    plotCols = ["Solar Charger [289]_PV power_"]
    outputData = pd.DataFrame(columns=plotCols)
    color = 'tab:red'
    for col in plotCols:
        pd.to_numeric(CaseStudyData[col])
        outputData[col] = CaseStudyData[col].resample('H').mean()
        ax1.plot(outputData[col], color=color)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('PV power (W)')
    # ax1.tick_params(axis='y', labelcolor=color)
    
    # Right hand axis for battery state
    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    plotCols = ['Battery Monitor [289]_State of charge_%']
    # plotCols = ['Solar Charger [289]_Charge state_','Solar Charger [274]_Charge state_']
    color = 'tab:blue'
    for col in plotCols:
        print(col)
        pd.to_numeric(CaseStudyData[col])
        outputData = CaseStudyData[~CaseStudyData.index.duplicated(keep='first')]
        outputData = outputData[col].dropna()
        outputData = outputData.resample('H').mean()
        ax2.plot(outputData, color=color,alpha=0.5)
    ax2.set_ylabel('Battery state of charge (%)')  # we already handled the x-label with ax1
    # ax2.tick_params(axis='y', labelcolor=color)
    
    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.show()
    
    #-----------------------------------------------------------------------------
    figRt = "../../Reporting/pyplots/"
    figName = "Solar charger properties"
    fig,ax1 = plt.subplots(figsize=(10,6))
    plt.title("Solar charger properties")
    
    # plotCols = ["Solar Charger [289]_PV power_","Solar Charger [274]_PV power_"]
    plotCols = ["Solar Charger [289]_PV power_"]
    outputData = pd.DataFrame(columns=plotCols)
    color = 'tab:red'
    for col in plotCols:
        pd.to_numeric(CaseStudyData[col])
        outputData[col] = CaseStudyData[col].resample('H').mean()
        ax1.plot(outputData[col], color=color)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('PV power (W)')
    # ax1.tick_params(axis='y', labelcolor=color)
    
    # Right hand axis for battery state
    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    plotCols = ['Solar Charger [274]_Charge state_']
    # plotCols = ['Solar Charger [289]_Charge state_','Solar Charger [274]_Charge state_']
    color = 'tab:blue'
    for col in plotCols:
        print(col)
        outputData = CaseStudyData[~CaseStudyData.index.duplicated(keep='first')]
        outputData = outputData[col].dropna()
        ax2.plot(outputData, color=color,alpha=0.5)
    ax2.set_ylabel('Charging state')  # we already handled the x-label with ax1
    # ax2.tick_params(axis='y', labelcolor=color)
    
    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.show()
    
    #-----------------------------------------------------------------------------
    figRt = "../../Reporting/pyplots/"
    figName = "Solar charger properties"
    fig,ax1 = plt.subplots(figsize=(10,6))
    plt.title("Solar charger properties")
    
    # plotCols = ["Solar Charger [289]_PV power_","Solar Charger [274]_PV power_"]
    plotCols = ["Solar Charger [289]_PV power_"]
    outputData = pd.DataFrame(columns=plotCols)
    color = 'tab:red'
    for col in plotCols:
        pd.to_numeric(CaseStudyData[col])
        outputData[col] = CaseStudyData[col].resample('H').mean()
        ax1.plot(outputData[col], color=color)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('PV power (W)')
    # ax1.tick_params(axis='y', labelcolor=color)
    
    # Right hand axis for battery state
    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    plotCols = ['Gateway [0]_Solar Irradiance_']
    # plotCols = ['Solar Charger [289]_Charge state_','Solar Charger [274]_Charge state_']
    color = 'tab:blue'
    for col in plotCols:
        print(col)
        outputData = CaseStudyData[~CaseStudyData.index.duplicated(keep='first')]
        outputData = outputData.apply(pd.to_numeric, errors='coerce')
        outputData = outputData[col].dropna()
        ax2.plot(outputData, color=color,alpha=0.5)
    ax2.set_ylabel('Solar irradiance')  # we already handled the x-label with ax1
    # ax2.tick_params(axis='y', labelcolor=color)
    
    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.show()
    
    #-----------------------------------------------------------------------------
    figRt = "../../Reporting/pyplots/"
    figName = "Solar charger properties"
    fig,ax1 = plt.subplots(figsize=(10,6))
    plt.title("Solar charger properties")
    
    # plotCols = ["Solar Charger [289]_PV power_","Solar Charger [274]_PV power_"]
    plotCols = ["Solar Charger [274]_PV power_"]
    outputData = pd.DataFrame(columns=plotCols)
    color = 'tab:red'
    for col in plotCols:
        pd.to_numeric(CaseStudyData[col])
        outputData[col] = CaseStudyData[col].resample('H').mean()
        ax1.plot(outputData[col], color=color)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('PV power (W)')
    # ax1.tick_params(axis='y', labelcolor=color)
    
    # Right hand axis for battery state
    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    plotCols = ['Solar Charger [274]_Current_A']
    # plotCols = ['Solar Charger [289]_Charge state_','Solar Charger [274]_Charge state_']
    color = 'tab:blue'
    for col in plotCols:
        print(col)
        outputData = CaseStudyData[~CaseStudyData.index.duplicated(keep='first')]
        outputData = outputData.apply(pd.to_numeric, errors='coerce')
        outputData = outputData[col].dropna()
        ax2.plot(outputData, color=color,alpha=0.5)
    ax2.set_ylabel('Current (A)')  # we already handled the x-label with ax1
    # ax2.tick_params(axis='y', labelcolor=color)
    
    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.show()
    
    #-----------------------------------------------------------------------------
    figRt = "../../Reporting/pyplots/"
    figName = "Solar charger properties"
    fig,ax1 = plt.subplots(figsize=(10,6))
    plt.title("Solar charger properties")
    
    # plotCols = ["Solar Charger [289]_PV power_","Solar Charger [274]_PV power_"]
    plotCols = ["Solar Charger [274]_PV power_"]
    outputData = pd.DataFrame(columns=plotCols)
    color = 'tab:red'
    for col in plotCols:
        pd.to_numeric(CaseStudyData[col])
        outputData[col] = CaseStudyData[col].resample('H').mean()
        ax1.plot(outputData[col], color=color)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('PV power (W)')
    # ax1.tick_params(axis='y', labelcolor=color)
    
    # Right hand axis for battery state
    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    plotCols = ['Solar Charger [289]_Voltage_V']
    # plotCols = ['Solar Charger [289]_Charge state_','Solar Charger [274]_Charge state_']
    color = 'tab:blue'
    for col in plotCols:
        print(col)
        outputData = CaseStudyData[~CaseStudyData.index.duplicated(keep='first')]
        outputData = outputData.apply(pd.to_numeric, errors='coerce')
        outputData = outputData[col].dropna()
        ax2.plot(outputData, color=color,alpha=0.5)
    ax2.set_ylabel('_Voltage_V')  # we already handled the x-label with ax1
    # ax2.tick_params(axis='y', labelcolor=color)
    
    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.show()
    
    #-----------------------------------------------------------------------------
    figRt = "../../Reporting/pyplots/"
    figName = "Solar charger properties"
    fig,ax1 = plt.subplots(figsize=(10,6))
    plt.title("Solar charger properties")
    
    # plotCols = ["Solar Charger [289]_PV power_","Solar Charger [274]_PV power_"]
    plotCols = ["Solar Charger [274]_PV power_"]
    outputData = pd.DataFrame(columns=plotCols)
    color = 'tab:red'
    for col in plotCols:
        pd.to_numeric(CaseStudyData[col])
        outputData[col] = CaseStudyData[col].resample('H').mean()
        ax1.plot(outputData[col], color=color)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('PV power (W)')
    # ax1.tick_params(axis='y', labelcolor=color)
    
    # Right hand axis for battery state
    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    plotCols = ['Solar Charger [274]_User yield_kWh']
    # plotCols = ['Solar Charger [289]_Charge state_','Solar Charger [274]_Charge state_']
    color = 'tab:blue'
    for col in plotCols:
        print(col)
        outputData = CaseStudyData[~CaseStudyData.index.duplicated(keep='first')]
        outputData = outputData.apply(pd.to_numeric, errors='coerce')
        outputData = outputData[col].dropna()
        ax2.plot(outputData, color=color,alpha=0.5)
    ax2.set_ylabel('User yield_kWh')  # we already handled the x-label with ax1
    # ax2.tick_params(axis='y', labelcolor=color)
    
    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.show()
    
    #--------------------------------------------------------------------------
    # Plot solcast (case study) irradiance vs PVGIS irradiance
    plt.figure(figsize=(10,6))
    outputData = CaseStudyData[~CaseStudyData.index.duplicated(keep='first')]
    outputData = outputData.apply(pd.to_numeric, errors='coerce')
    outputData = outputData['Gateway [0]_Solar Irradiance_'].dropna()
    plt.plot(outputData,label='Solcast (case study)',alpha=0.5)
    PVGIS = weatherData['ghi']
    plt.plot(PVGIS,alpha=0.5)
    plt.xlabel('Date')
    plt.ylabel('Solar irradiance')
    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.show()
    #--------------------------------------------------------------------------
    # plt.figure(figsize=(10,6))
    # # plotCols = ["Solar Charger [274]_PV power_","Solar Charger [289]_PV power_","Solar Charger [291]_PV power_"]
    # plotCols = ["Solar Charger [289]_PV power_","Solar Charger [274]_PV power_"]
    
    # outputData = pd.DataFrame(columns=plotCols)
    # for col in plotCols:
    #     pd.to_numeric(CaseStudyData[col])
    #     outputData[col] = CaseStudyData[col].resample('H').mean()
    #     outputData[col].plot(legend=True,alpha=0.9)
    # plt.xlabel('Date')
    # plt.ylabel('PV power (W)')
    # plt.title(figName)
    # plt.ylim(-100,3500)
    # plt.tight_layout()
    # plt.xlim('2023-09-01', '2023-10-01')   
    # plt.grid()
    # plt.show()
    # plt.savefig(figRt+figName+'.png', transparent=True)

