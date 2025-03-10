# -*- coding: utf-8 -*-
from __future__ import print_function
import multiprocessing
from demandGenerator import genDem
from demandGenerator2 import genDem2
import wntr
import wntr.network.controls as controls#(matheus)
import numpy as np
import pickle
import os
import shutil
#import csv
import pandas as pd#(matheus)import pandas
import time
import matplotlib.pyplot as plt
from wntr.epanet.util import *
#import sys

benchmark = os.getcwd()[:-17]+'Benchmarks\\'
try:
    os.makedirs(benchmark)
except:
    pass 

# demand-driven (DD) or pressure dependent demand (PDD) 
Mode_Simulation = 'PDD'#'PDD'#'PDD'

# Leak types
leak_time_profile = ["big", "small"]
sim_step_minutes = 30

# Set duration in hours
durationHours = 24*365 # One Year
timeStamp = pd.date_range("2024-01-01 00:00", "2024-12-30 23:55", freq=str(sim_step_minutes)+"min")

labelScenarios = []
uncertainty_Topology = 'NO'

# INP = "Hanoi"
INP = "Net1"
# INP = "ky18"
# INP = "Water Sensor Network 2"
# INP = "NJ1"
# INP = "PA1"
# INP = "ky1"
# INP = "ky2"
# INP = "ky8"
# INP = "modena"
# INP = "ky3"
# INP = "ky5"
# INP = "EPANET Net 3"

print(["Run input file: ", INP])
inp_file = 'networks/' + INP + '.inp'

INP_UNITS = FlowUnits.LPS

# RUN SCENARIOS
def runScenarios(scNum):

    itsok = False
    model_demand_increase_factor = 1#default value
    results_decimal_digits = 5#default value
    while itsok != True:
        try:
            qunc = np.arange(0, 0.25 ,0.05)
                
            # Path of EPANET Input File
            print("Scenario: "+str(scNum)+" start")
            
            wn = wntr.network.WaterNetworkModel(inp_file)
            inp = os.path.basename(wn.name)[0:-4]
            netName = benchmark+inp#+'2'

            # Create folder with network name
            if scNum==1:
                try:
                    #if os.path.exists(netName):
                    #    shutil.rmtree(netName)
                    #os.makedirs(netName)

                    #include specific controls for Net 3 network pump 10 to repeat daily
                    #exlude pump 335 bypass links and node from original net
                    if INP == "EPANET Net 3":
                        results_decimal_digits = 5
                        model_demand_increase_factor = 1
                        #for namee, controle in wn.controls():
                        #   print(namee, controle)                        
                        wn.remove_control('control 1')
                        wn.remove_control('control 2')
                        wn.remove_control('control 3')
                        wn.remove_control('control 4')
                        wn.remove_control('control 5')
                        wn.remove_control('control 6')
                        wn.remove_link('333')
                        wn.remove_link('330')
                        wn.remove_node('601')

                        pump = wn.get_link('335')
                        tank = wn.get_node('1')
                        act_pump_on = controls.ControlAction(pump, 'status', 1)
                        cond = controls.ValueCondition(tank, 'level', '<', 0.5)
                        ctrl = controls.Control(cond, act_pump_on, name='control_pump335_on')
                        wn.add_control('control_pump335_on', ctrl)

                        act_pump_off = controls.ControlAction(pump, 'status', 0)
                        cond = controls.ValueCondition(tank, 'level', '>', 5.8)
                        ctrl = controls.Control(cond, act_pump_off, name='control_pump335_off')
                        wn.add_control('control_pump335_off', ctrl)

                        pump = wn.get_link('10')
                        act_pump_on = controls.ControlAction(pump, 'status', 1)
                        act_pump_off = controls.ControlAction(pump, 'status', 0)
                        for i in range(1,8760,120):
                            cond = controls.SimTimeCondition(wn, '=', i*3600)
                            ctrl_name = 'control_pump10_on'+str(i)
                            ctrl = controls.Control(cond, act_pump_on, name=ctrl_name)
                            wn.add_control(ctrl_name, ctrl)

                            cond = controls.SimTimeCondition(wn, '=', (i+2)*3600)
                            ctrl_name = 'control_pump10_off'+str(i)
                            ctrl = controls.Control(cond, act_pump_off, name=ctrl_name)
                            wn.add_control(ctrl_name, ctrl)
                        
                        #for namee, controle in wn.controls():
                        #    print(namee, controle)

                    if INP == "Hanoi_CMH":
                        results_decimal_digits = 5
                        model_demand_increase_factor = 1

                    if INP == "Net1":
                        results_decimal_digits = 5
                        model_demand_increase_factor = 1

                    #increase all base demands by a user defined factor 
                    tempbase_demand = model_demand_increase_factor*wn.query_node_attribute('base_demand').to_numpy()
                    for w, junction in enumerate(wn.junction_name_list):
                        del wn.get_node(junction).demand_timeseries_list[0]
                        wn.get_node(junction).add_demand(tempbase_demand[w], None)
                        #print(wn.get_node(junction).demand_timeseries_list)

                    wntr.network.io.write_inpfile(wn, netName+'\\'+inp+'.inp', INP_UNITS, '2.2', False)
                except:
                    pass 
            else:
                wn = wntr.network.WaterNetworkModel(netName+'\\'+inp+'.inp')
                
            ## Energy pattern remove
            wn.options.energy.global_pattern = '""'#(matheus)wn.energy.global_pattern = '""'
            # Set time parameters
            wn.options.time.duration = durationHours*3600
            wn.options.time.hydraulic_timestep = 60*sim_step_minutes
            wn.options.time.quality_timestep = 0
            wn.options.time.report_timestep = 60*sim_step_minutes
            wn.options.time.pattern_timestep = 60*sim_step_minutes
            
            results = {}
            # Set random seed
            f=open('wn.pickle','wb')
            pickle.dump(wn,f)
            f.close()
            
            # Create fodler scenarios
            # Number of leaks at the same junction in day
            #(matheus)LEAK_LIST_TANK_JUNCTIONS = wn.junction_name_list+wn.tank_name_list
            
            if scNum == 1:
                nmLeaksNode = 0
            else:
                nmLeaksNode = int(round(np.random.uniform(1,2)))#leak off =0

            qunc_index = int(round(np.random.uniform(len(qunc)-1)))
            uncertainty_Length = qunc[qunc_index]
            
            qunc_index = int(round(np.random.uniform(len(qunc)-1)))
            uncertainty_Diameter = qunc[qunc_index]
            
            qunc_index = int(round(np.random.uniform(len(qunc)-1)))
            uncertainty_Roughness = qunc[qunc_index]
            
            qunc_index = int(round(np.random.uniform(len(qunc)-1)))
            uncertainty_base_demand = qunc[qunc_index]
            
            # CREATE FOLDER EVERY SCENARIO-I
            labels = np.zeros(len(timeStamp))#.astype(int)
            Sc = netName+'\\Scenario-'+str(scNum)
            if os.path.exists(Sc):
                shutil.rmtree(Sc)
            os.makedirs(Sc)
            
            ###########################################################################  
            ## SET BASE DEMANDS AND PATTERNS      
            # Remove all patterns
            #        # Initial base demands SET ALL EQUAL 1
            #if "ky" in INP:
            wn._patterns= {}#????????????????????
            tempbase_demand = wn.query_node_attribute('base_demand').to_numpy()#(matheus)tempbase_demand = wn.query_node_attribute('base_demand')
            
            #tempbase_demand = to_si(INP_UNITS, tempbase_demand, HydParam.Flow)
            #(matheus)tempbase_demand = np.array([tempbase_demand[i] for i, line in enumerate(tempbase_demand)])
            
            tmp = list(map(lambda x: x * uncertainty_base_demand, tempbase_demand))
            ql=tempbase_demand-tmp
            qu=tempbase_demand+tmp
            mtempbase_demand=len(tempbase_demand)
            qext_mtempbase_demand=ql+np.random.rand(mtempbase_demand)*(qu-ql)
            
            for w, junction in enumerate(wn.junction_name_list):
                #(matheus)wn.get_node(junction).demand_timeseries_list[0].base_value = qext_mtempbase_demand[w] #wn.query_node_attribute('base_demand')
                pattern_name = 'P_'+junction
                patts = genDem2()
                wn.add_pattern(pattern_name, patts)
                #(matheus)wn.get_node(junction).demand_pattern_name = pattern_name
                wn.get_node(junction).add_demand(qext_mtempbase_demand[w],pattern_name)#(matheus)
                del wn.get_node(junction).demand_timeseries_list[0]
                #print(wn.get_node(junction).demand_timeseries_list)
            
            ###########################################################################
            ## SET UNCERTAINTY PARAMETER
            # Uncertainty Length
            tempLengths = wn.query_link_attribute('length').to_numpy()#(matheus)tempLengths = wn.query_link_attribute('length')
            #(matheus)tempLengths = np.array([tempLengths[i] for i, line in enumerate(tempLengths)])
            tmp = list(map(lambda x: x * uncertainty_Length, tempLengths))
            ql=tempLengths-tmp
            qu=tempLengths+tmp
            mlength=len(tempLengths)
            qext=ql+np.random.rand(mlength)*(qu-ql)
                
            # Uncertainty Diameter
            tempDiameters = wn.query_link_attribute('diameter').to_numpy()#(matheus)tempDiameters = wn.query_link_attribute('diameter')
            #(matheus)tempDiameters = np.array([tempDiameters[i] for i, line in enumerate(tempDiameters)])
            tmp = list(map(lambda x: x * uncertainty_Diameter, tempDiameters))
            ql=tempDiameters-tmp
            qu=tempDiameters+tmp
            dem_diameter=len(tempDiameters)
            diameters=ql+np.random.rand(dem_diameter)*(qu-ql)
                
            # Uncertainty Roughness
            tempRoughness = wn.query_link_attribute('roughness').to_numpy()#(matheus)tempRoughness = wn.query_link_attribute('roughness')
            #(matheus)tempRoughness = np.array([tempRoughness[i] for i, line in enumerate(tempRoughness)])
            tmp = list(map(lambda x: x * uncertainty_Roughness, tempRoughness))
            ql=tempRoughness-tmp
            qu=tempRoughness+tmp
            dem_roughness=len(tempRoughness)
            qextR=ql+np.random.rand(dem_roughness)*(qu-ql)
            for w, line1 in enumerate(qextR):
                wn.get_link(wn.link_name_list[w]).roughness=line1
                wn.get_link(wn.link_name_list[w]).length=qext[w]
                wn.get_link(wn.link_name_list[w]).diameter=diameters[w]
                
            ###########################################################################    
            
            ## ADD A LEAK NODE 
            
            # Add leak node with 2 starttime end time
            leak_node = {}
            leak_diameter = {}
            leak_area = {}
            leak_type = {}
            time_of_failure = {}
            end_of_failure = {}
            leakStarts = {}
            leakEnds = {}
            leak_peak_time = {}
            #(matheus)i = int(round(np.random.uniform(wn.num_junctions+wn.num_tanks-1)))

            for leak_i in range(nmLeaksNode):
                i = int(round(np.random.uniform(wn.num_links-1)))
                leak_link = wn.get_link(wn.link_name_list[i])
                while leak_link.link_type != 'Pipe':
                    i = int(round(np.random.uniform(wn.num_links-1)))
                    leak_link = wn.get_link(wn.link_name_list[i])

                wn = wntr.morph.split_pipe(wn, wn.link_name_list[i], wn.link_name_list[i]+'l', 
                                           'leak_node'+str(leak_i), split_at_point = np.random.random_sample())
        
                leak_node[leak_i] = wn.get_node('leak_node'+str(leak_i))
            
                # Start Time of leak
                time_of_failure[leak_i] = int(np.round(np.random.uniform(1,len(timeStamp))))

                # End Time of leak
                end_of_failure[leak_i] = int(np.round(np.random.uniform(time_of_failure[leak_i],len(timeStamp))))
                
                # Labels for leak
                labels[time_of_failure[leak_i]:end_of_failure[leak_i]]=1

                ST = time_of_failure[leak_i] 
                ET = end_of_failure[leak_i]
                MT = ET
                leak_type[leak_i] = leak_time_profile[int(round(np.random.uniform(0,1)))]
                if leak_type[leak_i] == 'small':
                    leak_diameter[leak_i] = np.random.uniform(leak_link.diameter/25,  leak_link.diameter/5)
                else: #big
                    leak_diameter[leak_i] = np.random.uniform(leak_link.diameter/5,  leak_link.diameter)

                leak_area[leak_i]=3.14159*(leak_diameter[leak_i]/2)**2
                leak_start_time = ST*sim_step_minutes*60
                leak_end_time = ET*sim_step_minutes*60
                leak_node[leak_i].add_leak(wn, area = leak_area[leak_i], 
                                           start_time = leak_start_time,
                                           end_time = leak_end_time)

                leakStarts[leak_i] = timeStamp[ST]._date_repr + ' ' +timeStamp[ST]._time_repr
                leakEnds[leak_i] = timeStamp[ET-1]._date_repr + ' ' +timeStamp[ET-1]._time_repr
                leak_peak_time[leak_i] = timeStamp[MT-1]._date_repr+' '+timeStamp[MT-1]._time_repr
                
            ## SAVE EPANET INPUT FILE 
            # Write inp file
            wntr.network.io.write_inpfile(wn, Sc+'\\'+inp+'_Scenario-'+str(scNum)+'.inp', INP_UNITS, '2.2', False)#(matheus)wn.write_inpfile(Sc+'\\'+inp+'_Scenario-'+str(scNum)+'.inp')
            
            ## RUN SIMULATION WITH WNTR SIMULATOR
            wn.options.hydraulic.demand_model = Mode_Simulation
            sim = wntr.sim.WNTRSimulator(wn)#(matheus)sim = wntr.sim.WNTRSimulator(wn, mode=Mode_Simulation)
            results = sim.run_sim()
            print("Scenario "+str(scNum)+" simulation ok")#(matheus)
            if ((all(results.node['pressure']> 0)) !=True)==True:
                print("not run")
                scNum = scNum + 1
                return -1
            #except:
            #    print 'error'
            #    return -1
                
            # f=open('wn.pickle','rb')
            # wn = pickle.load(f)
            # f.close()
            
            def createFolder(path):
                if os.path.exists(path):
                    shutil.rmtree(path)
                os.makedirs(path)
            
            if results:
                ## CREATE FOLDERS FOR SCENARIOS
                #pressures_Folder = Sc+'\\Pressures'
                #createFolder(pressures_Folder)
                #dem_Folder = Sc+'\\Demands'
                #createFolder(dem_Folder)
                #flows_Folder = Sc+'\\Flows'
                #createFolder(flows_Folder)
                leaks_Folder = Sc+'\\Leaks'
                createFolder(leaks_Folder)
                print("Scenario "+str(scNum)+" folders created successfully")#(matheus)


                ## CREATE CSV FILES     
                for leak_i in range(nmLeaksNode):
                    fleaks2 = open(leaks_Folder+'\\Leak_'+str(leak_node[leak_i])+'_info.csv', 'w')
                    fleaks2.write("{} , {}\n".format('Description', 'Value'))
                    fleaks2.write("{} , {}\n".format('Leak Node', str(leak_node[leak_i])))
                    fleaks2.write("{} , {}\n".format('Leak Area', str(leak_area[leak_i])))
                    fleaks2.write("{} , {}\n".format('Leak Diameter', str(leak_diameter[leak_i])))
                    fleaks2.write("{} , {}\n".format('Leak Type', leak_type[leak_i]))
                    fleaks2.write("{} , {}\n".format('Leak Start', str(leakStarts[leak_i])))
                    fleaks2.write("{} , {}\n".format('Leak End', str(leakEnds[leak_i])))
                    fleaks2.close()
                    print("Scenario "+str(scNum)+" leak info "+str(leak_i+1)+"/"+str(nmLeaksNode)+" archive successfully saved")#(matheus)

                    # Leaks CSV
                    #(matheus)leaks = results.node['leak_demand',:,str(leak_node[leak_i])][0:-1]
                    leaks = results.node['leak_demand']#(matheus)
                    leaks = leaks.loc[:,leak_node[leak_i].name]#(matheus)
                    leaks = leaks[:len(timeStamp)]#(matheus)
                    leaks = from_si(INP_UNITS, leaks, HydParam.Flow)
                    leaks = leaks.round(results_decimal_digits)#(matheus)
                    print("Scenario "+str(scNum)+" leak_demand series "+str(leak_i+1)+"/"+str(nmLeaksNode)+" created successfully")#(matheus)

                    """(matheus)"""
                    leaks.index = timeStamp
                    fleaks = leaks_Folder+'\\Leak_'+leak_node[leak_i].name+'_demand.csv'
                    leaks.to_csv(fleaks)          
                    del fleaks, leaks
                    print("Scenario "+str(scNum)+" leak_demand "+str(leak_i+1)+"/"+str(nmLeaksNode)+" archive successfully saved")#(matheus)

                    """(matheus) leaks = [ round(elem, 6)*3600  for elem in leaks ]    
                    fleaks = pd.DataFrame(leaks)
                    fleaks['Timestamp'] = timeStamp
                    fleaks = fleaks.set_index(['Timestamp'])
                    fleaks.columns.values[0]='Description'
                    fleaks.to_csv(leaks_Folder+'\\Leak_'+str(leak_node[leak_i])+'_demand.csv')
                    del fleaks """
                
                print("Scenario "+str(scNum)+" leak data archives successfully saved")#(matheus)

                # Labels scenarios
                flabels = pd.DataFrame(labels)
                flabels['Timestamp'] = timeStamp
                flabels = flabels.set_index(['Timestamp'])
                flabels.columns.values[0]='Label'
                flabels.to_csv(Sc+'\\Labels.csv')
                del flabels
                
                print("Scenario "+str(scNum)+" labels archive successfully saved")#(matheus)


                """(matheus)"""
                pres = results.node['pressure']
                pres = pres[:len(timeStamp)]
                pres = from_si(INP_UNITS, pres, HydParam.Pressure)
                pres = pres.round(results_decimal_digits)
                pres.index = timeStamp
                fpres = Sc+'\\Node_pressures.csv'
                pres.to_csv(fpres)            
                del fpres, pres

                dem = results.node['demand']
                dem = dem[:len(timeStamp)]
                dem = from_si(INP_UNITS, dem, HydParam.Flow)
                dem = dem.round(results_decimal_digits)
                dem.index = timeStamp
                fdem = Sc+'\\Node_demands.csv'
                dem.to_csv(fdem)            
                del fdem, dem

                """(matheus) for j in range(0, wn.num_nodes):
            
                    pres = results.node['pressure'][wn.node_name_list[j]]
                    pres = pres[:len(timeStamp)]
                    pres = [ round(elem, 6) for elem in pres ]
                    #if ((all(results.node['pressure',:,:]> 0)) !=True)==True:
                        #print('Negative Pressures')
                    fpres = pd.DataFrame(pres)
                    fpres['Timestamp'] = timeStamp
                    fpres = fpres.set_index(['Timestamp'])
                    fpres.columns.values[0]='Value'
                    file_pres = pressures_Folder+'\\Node_'+str(wn.node_name_list[j])+'.csv'
                    fpres.to_csv(file_pres)            
                    del fpres, pres
                    
                    dem = results.node['demand'][wn.node_name_list[j]]
                    dem = dem[:len(timeStamp)]
        
                    dem = [ round(elem, 6) * 3600 for elem in dem ] 
                    fdem = pd.DataFrame(dem)
                    fdem['Timestamp'] = timeStamp
                    fdem = fdem.set_index(['Timestamp'])
                    fdem.columns.values[0]='Value'
                    fdem.to_csv(dem_Folder+'\\Node_'+str(wn.node_name_list[j])+'.csv')
                    del fdem, dem """

                """ (matheus) """
                flows = results.link['flowrate']
                flows = flows[:len(timeStamp)]
                flows = from_si(INP_UNITS, flows, HydParam.Flow)
                flows = flows.round(results_decimal_digits)
                flows.index = timeStamp
                fflows = Sc+'\\Link_flows.csv'
                flows.to_csv(fflows)            
                del fflows, flows
                    
                """(matheus) for j in range(0, wn.num_links):
                    flows = results.link['flowrate'][wn.link_name_list[j]]
                    flows = flows[:len(timeStamp)]
                    
                    flows = [ round(elem, 6) * 3600 for elem in flows ]
                    fflows = pd.DataFrame(flows)
                    fflows['Timestamp'] = timeStamp
                    fflows = fflows.set_index(['Timestamp'])
                    fflows.columns.values[0]='Value'
                    fflows.to_csv(flows_Folder+'\\Link_'+str(wn.link_name_list[j])+'.csv')
                    del fflows, flows """

                print("Scenario "+str(scNum)+" pressure/demand/flow archives successfully saved")#(matheus)

                fscenariosinfo = open(Sc+'\\Scenario-'+str(scNum)+'_info.csv', 'w')
                fscenariosinfo.write("Description , Value\n")     
                fscenariosinfo.write("{} , {}\n".format('Network_Name', inp))
                fscenariosinfo.write("{} , {}\n".format('Duration', str(durationHours)+' hours'))
                fscenariosinfo.write("{} , {}\n".format('Time_Step', str(wn.options.time.report_timestep/60)+' min'))
                fscenariosinfo.write("{} , {}\n".format('Uncertainty_Topology_(%)', uncertainty_Topology))
                fscenariosinfo.write("{} , {}\n".format('Uncertainty_Length_(%)', uncertainty_Length*100))
                fscenariosinfo.write("{} , {}\n".format('Uncertainty_Diameter_(%)', uncertainty_Diameter*100))
                fscenariosinfo.write("{} , {}\n".format('Uncertainty_Roughness_(%)', uncertainty_Roughness*100))
                #for j in range(0, wn.num_links):
                #    fscenariosinfo.write("{} , {}\n".format('Link_Status_'+wn.link_name_list[j], str(results.link['status', 0, wn.link_name_list[j]])))
                fscenariosinfo.close()
                itsok = True 
        
                #(matheus)if sum(labels)>0:
                #(matheus)    labelScenarios.append(1.0)
                #(matheus)else:
                #(matheus)    labelScenarios.append(0.0)

                print("Scenario "+str(scNum)+" finished")#(matheus)

                f=open('wn.pickle','rb')
                wn = pickle.load(f)
                f.close()

            else:
                print('results empty')
                return -1
        except:
            itsok = False
            print("Scenario "+str(scNum)+" exception")#(matheus)
            
    return 1
  

if __name__ == '__main__':

    t = time.time()
    
    NumScenarios = 501
    
    #Substitute incomplete or blank files scenarios, create missing scenarios
    scArray = range(1, NumScenarios)
    for i in scArray:
        try:
            error_count=0

            sc_path = benchmark + INP +'\\Scenario-'+str(i)
            archives_list = os.listdir(sc_path)
            if len(archives_list)>6:
                for archive in archives_list:
                    if os.path.getsize(sc_path+'\\'+archive)==0 and archive!='Leaks':
                        error_count+=1
            else:
                error_count+=1

            sc_path = benchmark + INP +'\\Scenario-'+str(i)+'\\Leaks'
            archives_list = os.listdir(sc_path)
            for archive in archives_list:
                if os.path.getsize(sc_path+'\\'+archive)==0:
                    error_count+=1

            if error_count!=0:
                runScenarios(i)
            else:
                print("Scenario "+str(i)+" ok")

        except:
            runScenarios(i)

    labelScenarios = []
    for i in scArray:
        labelScenarios.append(int(len(os.listdir(benchmark + INP +'\\Scenario-'+str(i)+'\\Leaks'))/2))

    flabels2 = pd.DataFrame(labelScenarios)
    flabels2['Scenario'] = scArray
    flabels2 = flabels2.set_index(['Scenario'])
    flabels2.columns.values[0]='Label'
    flabels2.to_csv(benchmark+ INP+'\\Labels.csv')
    del flabels2, labelScenarios

    print('Total Elapsed time is '+str(time.time() - t) + ' seconds.')

