""" FIDUCEO FCDR harmonisation 
    Author: Arta Dilo & Sam Hunt / NPL MM & ECO
    Date created: 06-10-2016
    Last update: 01-02-2017
Read matchup data from a netCDF file of a sensors pair, 
extract netCDF variables to be used in harmonisation, 
calculate the other harmonisation variables from netCDF vars. 
The read function rHDpair uses netCDF4 package to read the netCDF file, 
and numpy ndarrays to store harmonisation data. """

from datetime import datetime as dt
import netCDF4 as nc
import numpy as np
import os
import csv

""" Read netcdf of a sensors' pair to harmonisation data arrays """
def rHDpair(folder, filename):     
    pfn = os.path.join(folder, filename) # filename with path  
    print 'Opening netCDF file', pfn
    ncid = nc.Dataset(pfn,'r')
    
    Im = ncid.variables['lm'][:] # matchup index array
    H = ncid.variables['H'][:,:] # harmonisation variables; empty vars included
    Ur = ncid.variables['Ur'][:,:] # random uncertainty for H vars
    Us = ncid.variables['Us'][:,:] # systematic uncertainty for H vars
    K = ncid.variables['K'][:] # evaluated K adjustment values
    Kr = ncid.variables['Kr'][:] # matchup random uncertainty
    Ks = ncid.variables['Ks'][:] # systematic uncertainty for K values
    corIdx = ncid.variables['CorrIndexArray'][:] # matchup time; internal format
    corLen = ncid.variables['corrData'][:] # length of averaging window

    ncid.close()   

    ''' Compile ndarrays of harmonisation data '''
    nor = Im[0,2] # number of matchups in the pair
    
    if Im[0,0] == -1: # reference-sensor pair
        rspair = 1 
        
        # Extract non-empty columns: 0 [Lref], 
        # 5 [Cspace], 6 [Cict], 7 [CEarth], 8 [Lict], 9 [To]
        didx = [0, 5, 6, 7, 8, 9] # non-empty columns in H, Ur, Us
        H = H[:,didx] 
        Ur = Ur[:,didx] 
        Us = Us[:,didx] 
        
        # create data and uncertainty arrays
        noc = H.shape[1] + 1 # plus one column for K data

        # data variables
        Hdata = np.zeros((nor, noc)) 
        Hdata[:,:-1] = H
        Hdata[:,noc-1] = K # adjustment values in last column
        
        # random uncertainties 
        Hrnd = np.zeros((nor, noc)) 
        Hrnd[:,:-1] = Ur
        Hrnd[:,noc-1] = Kr
        
        # systematic uncertainty
        Hsys = np.zeros((nor, noc)) 
        Hsys[:,:-1] = Us
        Hsys[:,noc-1] = Ks
        
    else: # sensor-sensor pair
        rspair = 0 
        noc = H.shape[1] + 2 # plus two columns for K data and Lref
        
        Hdata = np.zeros((nor, noc)) 
        Hdata[:,1:11] = H
        Hdata[:,noc-1] = K # adjustment values in last column       

        # random uncertainties 
        Hrnd = np.zeros((nor, noc)) 
        Hrnd[:,1:11] = Ur
        Hrnd[:,noc-1] = Kr

         # systematic uncertainty
        Hsys = np.zeros((nor, noc)) 
        Hsys[:,1:11] = Us
        Hsys[:,noc-1] = Ks
       
    return rspair,Im,Hdata,Hrnd,Hsys,corIdx,corLen
    #return rspair,Im,Hdata,Hrnd,corIdx

""" Extract sensors from a list of netCDF files """
def sensors(nclist):
   fsl = [] # list of sensor labels in nclist
   for netcdf in nclist:
       s1 = netcdf[0:3]
       s2 = netcdf[4:7]
       
       if s1 not in fsl:
           fsl.append(s1)           
       if s2 not in fsl:
           fsl.append(s2)
   return fsl

""" Get input calibration coefficients of sensors in netCDF filelist """
def sInCoeff(csvfolder, nclist):
   fsl = sensors(nclist) # list of sensors in nc files 
   
   inCc = {} # dictionary of fsl sensors input coefficients
   cfn = os.path.join(csvfolder, 'CalCoeff.csv')
   with open(cfn, 'rb') as f:
       reader = csv.reader(f)
       reader.next() # skip header
       for row in reader:
           sl = row[0] # sensor label
           coefs = np.array(row[1:5]).astype('float')
           if sl in fsl:
               inCc[sl] = coefs
   return inCc

""" Create harmonisation data from netcdf files in the list.
Data matrix with fixed number of columns, 14, and number of rows equal to 
number of matchups observations for the whole series. """                
def rHData(folder, nclist):
    fsl = sensors(nclist) # list of sensors; same order as coeffs array
    # initialise harmonisation data arrays 
    Im = np.empty([0,3], dtype=int) # matrix index for pairs
    Hdata = np.empty([0,14], order = 'C')
    Hrnd = np.empty([0,14], order = 'C')
    tidx = np.empty([0]) # array of matchup times

    # loop through the netCDFs filelist 
    for ncfile in nclist:
        # read harmonisation data, variables and uncertainties
        rsp,lm,Hd,Hr,Hs,corIdx,corLen = rHDpair(folder, ncfile)
        #rsp,lm,Hd,Hr,corIdx = rHDpair(folder, ncfile)
        print 'NetCDF data from', ncfile, 'passed to harmonisation variables.'
        
        nor = lm[0,2] # no of matchups for the current pair
        tH = np.zeros((nor, 14))
        tHr = np.zeros((nor, 14)) # last two columns unused; to keep same shape
        if rsp: # reference-sensor pair
            tH[:,0] = Hd[:,0] # reference radiance
            tH[:,1].fill(1.) # space counts 1st sensor
            tH[:,3].fill(1.) # Earth counts 1st sensor
            tH[:,6:12] = Hd[:,1:7] # 2nd sensor calibration data
            tHr[:,0] = Hr[:,0] # reference radiance random uncertainty
            tHr[:,6:12] = Hr[:,1:7] # 2nd sensor random uncertainty data
            sl1 = 'm02'# 1st sensor label
        else: # sensor-sensor pair
            tH[:,1:12] = Hd[:,0:11] # 1st and 2nd sensor calibration data
            tHr[:,1:12] = Hr[:,0:11] # 1st and 2nd sensor random uncertainty 
            sl1 = 'n' + str(lm[0,0]) # 1st sensor label
        sidx1 = fsl.index(sl1) # index in the list of sensors
        sl2 = 'n' + str(lm[0,1]) # 2nd sensor label
        sidx2 = fsl.index(sl2) # index in the list of sensors
        tH[:,12] = sidx1 # 1st sensor's index in coeffs array 
        tH[:,13] = sidx2 # 2nd sensor's index
        tHr[:,12].fill(1.)
        tHr[:,13].fill(1.)
        
        # add data of the current pair to harmonisation arrays
        Im = np.append(Im, lm, axis=0)
        Hdata = np.append(Hdata, tH, axis=0)
        Hrnd = np.append(Hrnd, tHr, axis=0)
        tidx = np.append(tidx, corIdx)
        
    return Im, Hdata, Hrnd, tidx
    
""" Sam's function for time coversion:
Return unix time in seconds (from 1970) from AVHRR time in seconds (from 1975)"""
def conv2date(inTime):
    # Calculate difference from AVHRR start time and unix start time in seconds
    start_time_AVHRR = dt(1975, 1, 1)
    start_time_unix = dt(1970, 1, 1)
    time_diff = (start_time_AVHRR - start_time_unix).total_seconds()

    # Convert to time from 1975 to date
    outTime = [dt.fromtimestamp(time+time_diff) for time in inTime]

    return outTime