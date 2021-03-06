"""
Generate the required W matrices for a given harmonisation match-up file and add them to the file

Usage:
python add_W_to_matchup_file.py path/to/matchup/file.nc
"""

'''___Python Modules___'''
from sys import argv

'''___Third Party Modules___'''
from numpy import array, int8, ones, where, isnan, nan, bool_
from netCDF4 import Dataset

'''___Harmonisation Modules___'''
from W_matrix_functions import return_w_matrix_variables
from harmonisation_input_checker import main as test_input_file
from generate_w_matrices import generate_rolling_average_w_matrix

'''___Authorship___'''
__author__ = ["Sam Hunt"]
__created__ = "23/08/2017"
__credits__ = ["Ralf Quast", "Jon Mittaz", "Peter Harris"]
__version__ = "0.0"
__maintainer__ = "Sam Hunt"
__email__ = "sam.hunt@npl.co.uk"
__status__ = "Development"


def read_matchup_data(file_path):
    """
    Return time data from harmonisation match-up file

    :type file_path: str
    :param file_path: path of match-up file

    :return:
        :lm: *numpy.ndarray*

        Stores satellite pairs with number of entries

        :H: *numpy.ndarray*

        Radiances and counts per matchup

        :Us: *numpy.ndarray*

        Systematic uncertainties for H array

        :Ur: *numpy.ndarray*

        Random uncertainties for H array

        :K: *numpy.ndarray*

        K (sensor-to-sensor differences) for zero shift case

        :Kr: *numpy.ndarray*

        K (sensor-to-sensor differences) random uncertainties (matchup uncertainty)

        :Ks: *numpy.ndarray*

        K (sensor-to-sensor differences) systematic uncertainties for zero shift case

        :sensor_1_name: *int*

        sensor 1 ID

        :sensor_2_name: *int*

        sensor 2 ID

        :time_sensor_1: *numpy.ndarray*

        Match-up times for sensor 1

        :time_sensor_2: *numpy.ndarray*

        Match-up times for sensor 2

        :u_C_S_sensor_1: *numpy.ndarray*

        Scanline uncertainties for space counts for the reference sensor

        :u_C_ICT_sensor_1: *numpy.ndarray*

        Scanline uncertainties for internal calibration target counts for the reference sensor

        u_C_S_sensor_2: *numpy.ndarray*

        Scanline uncertainties for space counts for the sensor

        :u_C_ICT_sensor_2: *numpy.ndarray*

        Scanline uncertainties for internal calibration target counts for the sensor
    """

    rootgrp = Dataset(file_path)
    H = rootgrp.variables["H"][:]
    Us = rootgrp.variables["Us"][:]
    Ur = rootgrp.variables["Ur"][:]
    K = rootgrp.variables["K"][:]
    Kr = rootgrp.variables["Kr"][:]
    Ks = rootgrp.variables["Ks"][:]
    sensor_1_name = rootgrp.variables["lm"][0, 0]
    sensor_2_name = rootgrp.variables["lm"][0, 1]
    time_sensor_1 = rootgrp.variables["ref_time_matchup"][:]
    time_sensor_2 = rootgrp.variables["time_matchup"][:]
    u_C_S_sensor_1 = rootgrp.variables['ref_cal_Sp_Ur'][:, :]
    u_C_ICT_sensor_1 = rootgrp.variables['ref_cal_BB_Ur'][:, :]
    u_C_S_sensor_2 = rootgrp.variables['cal_Sp_Ur'][:, :]
    u_C_ICT_sensor_2 = rootgrp.variables['cal_BB_Ur'][:, :]
    rootgrp.close()

    return H, Us, Ur, K, Kr, Ks, sensor_1_name, sensor_2_name, time_sensor_1, time_sensor_2, \
           u_C_S_sensor_1, u_C_ICT_sensor_1, u_C_S_sensor_2, u_C_ICT_sensor_2


def return_valid_averages_mask(u11, u12, u21, u22, label=nan):
    """
    Mask array for match-ups generated from a full averaging kernel

    :type u11: numpy.ndarray
    :param u11: scanline uncertainties of space counts for sensor 1

    :type u12: numpy.ndarray
    :param u12: scanline uncertainties of black body counts for sensor 1

    :type u21: numpy.ndarray
    :param u21: scanline uncertainties of space counts for sensor 2

    :type u22: numpy.ndarray
    :param u22: scanline uncertainties of black body counts for sensor 2

    :type label: float/int/nan
    :type label: value in uncertainties array to indicate bad data

    :return:
        :valid_averages: *numpy.ndarray*

        Mask of valid match-ups
    """

    valid_averages = ones(u11.shape[0], dtype=bool_)

    if isnan(label):
        # If NaN provided for any scanline uncertainty match-up invalid
        for i, (row11, row12, row21, row22) in enumerate(zip(u11, u12, u21, u22)):
            if (where(isnan(row11))[0].size != 0) or (where(isnan(row12))[0].size != 0) or \
                    (where(isnan(row21))[0].size != 0) or (where(isnan(row22))[0].size != 0):
                valid_averages[i] = False

    return valid_averages


def return_w_matrices(u_C_S_sensor_1, u_C_ICT_sensor_1, u_C_S_sensor_2, u_C_ICT_sensor_2,
                      time_sensor_1, width_sensor_1, time_sensor_2, width_sensor_2, sensor_i_name):

    """
    Return w matrices and uncertainty vectors for a match-up

    :type u_C_S_sensor_1: numpy.ndarray
    :param u_C_S_sensor_1: Scanline uncertainties for space counts for sensor 1

    :type u_C_ICT_sensor_1: numpy.ndarray
    :param u_C_ICT_sensor_1: Scanline uncertainties for ICT counts for sensor 1

    :type u_C_S_sensor_2: numpy.ndarray
    :param u_C_S_sensor_2: Scanline uncertainties for space counts for sensor 2

    :type u_C_ICT_sensor_2: numpy.ndarray
    :param u_C_ICT_sensor_2: Scanline uncertainties for ICT counts for sensor 2

    :type time_sensor_1: numpy.ndarray
    :param time_sensor_1: match-up time for sensor 1

    :type width_sensor_1: float
    :param width_sensor_1: scanline time for sensor 1

    :type time_sensor_2: numpy.ndarray
    :param time_sensor_2: match-up time for sensor 2

    :type width_sensor_2: float
    :param width_sensor_2: scanline time for sensor 2

    :type sensor_i_name: int
    :param sensor_i_name: sensor 1 ID

    :return:
        :W: *scipy.sparse.csr_matrix*
        weighting matrix
        :uncertainty_vector: *numpy.ndarray*
        scanline uncertainty vector
    """

    # 1. Build w matrix and uncertainty vectors for Sensor 2
    w_C_S_sensor_2, uncertainty_vector_S_sensor_2 = generate_rolling_average_w_matrix(time_sensor_2, width_sensor_2, u_C_S_sensor_2)
    _, uncertainty_vector_ICT_sensor_2 = generate_rolling_average_w_matrix(time_sensor_2, width_sensor_2, u_C_ICT_sensor_2)

    w_matrices = [w_C_S_sensor_2]
    uncertainty_vectors = [uncertainty_vector_S_sensor_2, uncertainty_vector_ICT_sensor_2]

    # 2. Build w matrix and uncertainty vectors for Sensor 1 (if not reference)
    if sensor_i_name != -1:
        # a. Compute W data
        w_C_S_sensor_1, uncertainty_vector_S_sensor_1 = generate_rolling_average_w_matrix(time_sensor_1, width_sensor_1, u_C_S_sensor_1)
        _, uncertainty_vector_ICT_sensor_1 = generate_rolling_average_w_matrix(time_sensor_1, width_sensor_1, u_C_ICT_sensor_1)
        w_matrices = [w_C_S_sensor_1, w_C_S_sensor_2]
        uncertainty_vectors = [uncertainty_vector_S_sensor_1, uncertainty_vector_ICT_sensor_1,
                               uncertainty_vector_S_sensor_2, uncertainty_vector_ICT_sensor_2]

    return w_matrices, uncertainty_vectors


def write_input_file(file_path, X1, X2, Ur1, Ur2, Us1, Us2, uncertainty_type1, uncertainty_type2, K, Kr, Ks,
                     time1, time2, sensor_1_name, sensor_2_name, additional_variables=None):
    """
    Write harmonisation input file from input data arrays (no w matrix variables, see func append_W_to_input_file(...)
    for this functionality)

    :type file_path: str
    :param file_path: match-up file path

    :type X1: numpy.ndarray
    :param X1: Radiances and counts per matchup for sensor 1

    :type X2: numpy.ndarray
    :param X2: Radiances and counts per matchup for sensor 2

    :type Ur1: numpy.ndarray
    :param Ur1: Random uncertainties for X1 array

    :type Ur2: numpy.ndarray
    :param Ur2: Random uncertainties for X2 array

    :type Us1: numpy.ndarray
    :param Us1: Systematic uncertainties for X1 array

    :type Us2: numpy.ndarray
    :param Us2: Systematic uncertainties for X2 array

    :type uncertainty_type1: numpy.ndarray
    :param uncertainty_type1: Uncertainty correlation type per X1 column

    :type uncertainty_type2: numpy.ndarray
    :param uncertainty_type2: Uncertainty correlation type per X2 column

    :type K: numpy.ndarray
    :param K: K (sensor-to-sensor differences) for zero shift case

    :type Kr: numpy.ndarray
    :param Kr: K (sensor-to-sensor differences) random uncertainties (matchup uncertainty)

    :type Ks: numpy.ndarray
    :param Ks: K (sensor-to-sensor differences) systematic uncertainties for zero shift case

    :type time1: numpy.ndarray
    :param time1: "Match-up time sensor 1, seconds since 1970-01-01"

    :type time2: numpy.ndarray
    :param time2: "Match-up time sensor 2, seconds since 1970-01-01"

    :type sensor_1_name: int
    :param sensor_1_name: sensor i ID

    :type sensor_2_name: int
    :param sensor_2_name: sensor j ID

    :type additional_variables: dict
    :param additional_variables: dictionary of additional, non-required variable to add to harmonisation input files. To
    be for e.g. testing, diagnostics etc.

    One dictionary entry per additional variable, with each entry as:

    "variable_name": {"data": data_array, "dtype": dtype_str, "dim": dim_tuple, "Description", desc_str}

    where:
    * data_array(*numpy.ndarray*) - array variable data
    * dtype_str(*str*) - netCDF variable data type (e.g. "i4", "f8", ...)
    * dim_tuple(*tuple:str*) - tuple of the variable dimension names (e.g. ('M',) )
    * desc_str(*str*) - description of the variable
    """

    # 1. Open file
    rootgrp = Dataset(file_path, mode='w')

    # 2. Create attributes
    rootgrp.sensor_1_name = sensor_1_name
    rootgrp.sensor_2_name = sensor_2_name

    # 2. Create dimensions
    # > M - number of matchups
    M_dim = rootgrp.createDimension("M", X1.shape[0])

    # > m - number of columns in X1 and X2 arrays
    m1_dim = rootgrp.createDimension("m1", X1.shape[1])
    m2_dim = rootgrp.createDimension("m2", X2.shape[1])

    # 3. Create new variables

    # > X1 - Radiances and counts per matchup for sensor 1
    X1_var = rootgrp.createVariable('X1', 'f4', ('M', 'm1'), zlib=True, complevel=9)
    X1_var.description = "Radiances and counts per matchup for sensor 1"
    X1_var[:] = X1[:]

    # > X2 - Radiances and counts per matchup for sensor 2
    X2_var = rootgrp.createVariable('X2', 'f4', ('M', 'm2'), zlib=True, complevel=9)
    X2_var.description = "Radiances and counts per matchup for sensor 2"
    X2_var[:] = X2[:]

    # > Ur1 - Random uncertainties for X1 array
    Ur1_var = rootgrp.createVariable('Ur1', 'f4', ('M', 'm1'), zlib=True, complevel=9)
    Ur1_var.description = "Random uncertainties for X1 array"
    Ur1_var[:] = Ur1[:]

    # > Ur2 - Random uncertainties for X2 array
    Ur2_var = rootgrp.createVariable('Ur2', 'f4', ('M', 'm2'), zlib=True, complevel=9)
    Ur2_var.description = "Random uncertainties for X2 array"
    Ur2_var[:] = Ur2[:]

    # > Us1 - Systematic uncertainties for X1 array
    Us1_var = rootgrp.createVariable('Us1', 'f4', ('M', 'm1'), zlib=True, complevel=9)
    Us1_var.description = "Systematic uncertainties for X1 array"
    Us1_var[:] = Us1[:]

    # > Us2 - Systematic uncertainties for X2 array
    Us2_var = rootgrp.createVariable('Us2', 'f4', ('M', 'm2'), zlib=True, complevel=9)
    Us2_var.description = "Systematic uncertainties for X2 array"
    Us2_var[:] = Us2[:]

    # > uncertainty_type1 - Uncertainty correlation type per X1 column
    uncertainty_type1_var = rootgrp.createVariable('uncertainty_type1', 'i4', ('m1',), zlib=True, complevel=9)
    uncertainty_type1_var.description = "Uncertainty correlation type per X1 column, labelled as, " + \
                                       "(1) Independent Error Correlation, " + \
                                       "(2) Independent + Systematic Error Correlation, or " + \
                                       "(3) Structured Error Correlation"
    uncertainty_type1_var[:] = uncertainty_type1[:]

    # > uncertainty_type2 - Uncertainty correlation type per X2 column
    uncertainty_type2_var = rootgrp.createVariable('uncertainty_type2', 'i4', ('m2',), zlib=True, complevel=9)
    uncertainty_type2_var.description = "Uncertainty correlation type per X2 column, labelled as, " + \
                                        "(1) Independent Error Correlation, " + \
                                        "(2) Independent + Systematic Error Correlation, or " + \
                                        "(3) Structured Error Correlation"
    uncertainty_type2_var[:] = uncertainty_type2[:]

    # > K - K (sensor-to-sensor differences) for zero shift case
    K_var = rootgrp.createVariable('K', 'f4', ('M',), zlib=True, complevel=9)
    K_var.description = "K (sensor-to-sensor differences) for zero shift case"
    K_var[:] = K[:]

    # > Kr - K (sensor-to-sensor differences) random uncertainties (matchup uncertainty)
    Kr_var = rootgrp.createVariable('Kr', 'f4', ('M',), zlib=True, complevel=9)
    Kr_var.description = "K (sensor-to-sensor differences) random uncertainties (matchup uncertainty)"
    Kr_var[:] = Kr[:]

    # > Ks - K (sensor-to-sensor differences) systematic uncertainties for zero shift case
    Ks_var = rootgrp.createVariable('Ks', 'f4', ('M',), zlib=True, complevel=9)
    Ks_var.description = "K (sensor-to-sensor differences) systematic uncertainties for zero shift case"
    Ks_var[:] = Ks[:]

    # > time1 - Sensor 1 time of match-up
    time1_var = rootgrp.createVariable('time1', 'f8', ('M',), zlib=True, complevel=9)
    time1_var.description = "Match-up time sensor 1, seconds since 1970-01-01"
    time1_var[:] = time1[:]

    # > time 2 - Sensor 2 time of match-up
    time2_var = rootgrp.createVariable('time2', 'f8', ('M',), zlib=True, complevel=9)
    time2_var.description = "Match-up time sensor 2, seconds since 1970-01-01"
    time2_var[:] = time2[:]

    # > additional variables - non-required variable to add to harmonisation input files
    if additional_variables is not None:
        for variable in additional_variables.keys():
            additional_var = rootgrp.createVariable(variable, additional_variables[variable]['dtype'],
                                                    additional_variables[variable]['dim'], zlib=True, complevel=9)
            additional_var.Description = additional_variables[variable]['Description']
            additional_var[:] = additional_variables[variable]['data'][:]

    # 5. Close file
    rootgrp.close()

    return 0


def append_W_to_input_file(filepath,
                           w_matrix_val, w_matrix_row, w_matrix_col, w_matrix_nnz,
                           u_matrix_row_count, u_matrix_val,
                           w_matrix_use1, w_matrix_use2, u_matrix_use1, u_matrix_use2):
    """
    Append set of W matrix variable arrays to a given harmonisation input file

    :type w_matrix_val: numpy.ndarray
    :param w_matrix_val: Concatenated array of non-zero elements of W matrices

    :type w_matrix_row: numpy.ndarray
    :param w_matrix_row: Concatenated array of row indices of W matrices

    :type w_matrix_col: numpy.ndarray
    :param w_matrix_col: Concatenated array of row indices of W matrices

    :type w_matrix_nnz: numpy.ndarray
    :param w_matrix_nnz: Number of non-zeros elements per W matrix

    :type u_matrix_row_count: numpy.ndarray
    :param u_matrix_row_count: Number of non-zero elements per u matrix

    :type u_matrix_val: numpy.ndarray
    :param u_matrix_val: Concatenated array of u matrix non-zero values

    :type w_matrix_use1: numpy.ndarray
    :param w_matrix_use1: mapping from X1 array column index to W

    :type w_matrix_use2: numpy.ndarray
    :param w_matrix_use2: mapping from X2 array column index to W

    :type u_matrix_use1: numpy.ndarray
    :param u_matrix_use1: a mapping from X1 array column index to U

    :type u_matrix_use2: numpy.ndarray
    :param u_matrix_use2: a mapping from X2 array column index to U
    """

    # 1. Open file
    rootgrp = Dataset(filepath, mode='a')

    # 2. Create dimensions
    # > w_matrix_count - number of W matrices
    w_matrix_count_dim = rootgrp.createDimension("w_matrix_count", len(w_matrix_nnz))

    # > w_matrix_row - number of rows in each w matrix
    if len(w_matrix_row.shape) > 1:
        num_row = w_matrix_row.shape[1]
    else:
        num_row = len(w_matrix_row)
    w_matrix_row_count_dim = rootgrp.createDimension("w_matrix_row_count", num_row)

    # > w_matrix_sum_nnz - sum of non-zero elements in all W matrices
    w_matrix_nnz_sum_dim = rootgrp.createDimension("w_matrix_nnz_sum", sum(w_matrix_nnz))

    # > u_matrix_count - number of u matrices
    u_matrix_count_dim = rootgrp.createDimension("u_matrix_count", len(u_matrix_row_count))

    # > u_matrix_row_count_sum - sum of rows in u matrices
    u_matrix_row_count_sum_dim = rootgrp.createDimension("u_matrix_row_count_sum", sum(u_matrix_row_count))

    # 3. Create new variables
    # > w_matrix_nnz - number of non-zero elements for each W matrix
    w_matrix_nnz_var = rootgrp.createVariable('w_matrix_nnz', 'i4', ('w_matrix_count',), zlib=True, complevel=9)
    w_matrix_nnz_var.description = "number of non-zero elements for each W matrix"

    # > w_matrix_row - CSR row numbers for each W matrix
    row_dims = ('w_matrix_row_count',)
    if len(w_matrix_row.shape) > 1:
        row_dims = ('w_matrix_count', 'w_matrix_row_count')
    w_matrix_row_var = rootgrp.createVariable('w_matrix_row', 'i4', row_dims, zlib=True, complevel=9)
    w_matrix_row_var.description = "CSR row numbers for each W matrix"

    # > w_matrix_col - CSR column numbers for all W matrices
    w_matrix_col_var = rootgrp.createVariable('w_matrix_col', 'i4', ('w_matrix_nnz_sum',), zlib=True, complevel=9)
    w_matrix_col_var.description = "CSR column numbers for all W matrices"

    # > w_matrix_val - CSR values for all W matrices
    w_matrix_val_var = rootgrp.createVariable('w_matrix_val', 'f4', ('w_matrix_nnz_sum',), zlib=True, complevel=9)
    w_matrix_val_var.description = "CSR values for all W matrices"

    # > w_matrix_use1 - a mapping from X2 array column index to W
    w_matrix_use1_var = rootgrp.createVariable('w_matrix_use1', 'i4', ('m1',), zlib=True, complevel=9)
    w_matrix_use1_var.description = "mapping from X1 array column index to W"

    # > w_matrix_use2 - a mapping from X2 array column index to W
    w_matrix_use2_var = rootgrp.createVariable('w_matrix_use2', 'i4', ('m2',), zlib=True, complevel=9)
    w_matrix_use2_var.description = "mapping from X2 array column index to W"

    # > u_matrix_row_count - number of rows of each u matrix
    u_matrix_row_count_var = rootgrp.createVariable('u_matrix_row_count', 'i4',
                                                              ('u_matrix_count',), zlib=True, complevel=9)
    u_matrix_row_count_var.description = "number of rows of each u matrix"

    # > u matrix val - uncertainty of each scanline value
    u_matrix_val_var = rootgrp.createVariable('u_matrix_val', 'f4', ('u_matrix_row_count_sum',),
                                                    zlib=True, complevel=9)
    u_matrix_val_var.description = "u matrix non-zero diagonal elements"

    # > u_matrix_use1 - a mapping from X1 array column index to U
    u_matrix_use1_var = rootgrp.createVariable('u_matrix_use1', 'i4', ('m1',), zlib=True, complevel=9)
    u_matrix_use1_var.description = "mapping from X1 array column index to U"

    # > u_matrix_use2 - a mapping from X2 array column index to U
    u_matrix_use2_var = rootgrp.createVariable('u_matrix_use2', 'i4', ('m2',), zlib=True, complevel=9)
    u_matrix_use2_var.description = "mapping from X2 array column index to U"

    # 4. Add data
    w_matrix_nnz_var[:] = w_matrix_nnz[:]
    w_matrix_row_var[:] = w_matrix_row[:]
    w_matrix_col_var[:] = w_matrix_col[:]
    w_matrix_val_var[:] = w_matrix_val[:]
    w_matrix_use1_var[:] = w_matrix_use1[:]
    w_matrix_use2_var[:] = w_matrix_use2[:]

    u_matrix_row_count_var[:] = u_matrix_row_count[:]
    u_matrix_val_var[:] = u_matrix_val[:]
    u_matrix_use1_var[:] = u_matrix_use1[:]
    u_matrix_use2_var[:] = u_matrix_use2[:]

    # 5. Close file
    rootgrp.close()

    return 0


def main(input_file_path, output_file_path):
    """
    Routine to update Jon's AVHRR harmonisation matchup file to include w variables and match newest spec

    :type input_file_path: str
    :param input_file_path: path of input harmonisation input file

    :type output_file_path: str
    :param output_file_path: path of output harmonisation input file
    """

    # 1. Read required data to generate W matrices
    print "Reading file:", input_file_path
    H, Us, Ur, K, Kr, Ks, sensor_1_name, sensor_2_name, \
        time_sensor_1, time_sensor_2, u_C_S_sensor_1, u_C_ICT_sensor_1, \
            u_C_S_sensor_2, u_C_ICT_sensor_2 = read_matchup_data(input_file_path)

    # Find bad data to remove:
    # > Determine valid scanlines (i.e. full averaging kernal available)
    valid_averages = return_valid_averages_mask(u_C_S_sensor_1, u_C_ICT_sensor_1, u_C_S_sensor_2, u_C_ICT_sensor_2)

    # > Remove incorrect assignment in Ur array
    if sensor_1_name != -1:
        Ur[:, [0, 1, 5, 6]] = 0
    else:
        Ur[:, [5, 6]] = 0
        Us[:, 0] = 0
    # > Define X1, X2, Ur1, Ur2, Us1 and Us2 arrays
    m1 = 5
    m2 = 5
    if sensor_1_name == -1:
        m1 = 1
    elif (H[:, 9] == 0).all():
        m1 = 4
    if (H[:, 9] == 0).all():
        m2 = 4

    X1 = H[valid_averages, :m1]
    Ur1 = Ur[valid_averages, :m1]
    Us1 = Us[valid_averages, :m1]
    X2 = H[valid_averages, 5:5+m2]
    Ur2 = Ur[valid_averages, 5:5+m2]
    Us2 = Us[valid_averages, 5:5+m2]

    del H, Ur, Us

    # 2. Generate required W matrix variables
    print "Generating W Matrix Variables from data..."

    # a. Generate lists of W matrices and uncertainty vectors
    w_matrices, uncertainty_vectors = return_w_matrices(u_C_S_sensor_1[valid_averages, :],
                                                        u_C_ICT_sensor_1[valid_averages, :],
                                                        u_C_S_sensor_2[valid_averages, :],
                                                        u_C_ICT_sensor_2[valid_averages, :],
                                                        time_sensor_1[valid_averages], 0.5,
                                                        time_sensor_2[valid_averages], 0.5,
                                                        sensor_1_name)
    del u_C_S_sensor_1, u_C_ICT_sensor_1, u_C_S_sensor_2, u_C_ICT_sensor_2

    # b. Convert W matrices and uncertainty vector to input file variables
    w_matrix_val, w_matrix_row, w_matrix_col, w_matrix_nnz, \
        uncertainty_vector_row_count, uncertainty_vector = return_w_matrix_variables(w_matrices, uncertainty_vectors)
    del w_matrices, uncertainty_vectors

    # c. Assign type/use matrices
    w_matrix_use1 = array([1, 1, 0, 0, 0], dtype=int8)
    w_matrix_use2 = array([2, 2, 0, 0, 0], dtype=int8)
    uncertainty_vector_use1 = array([1, 2, 0, 0, 0], dtype=int8)
    uncertainty_vector_use2 = array([3, 4, 0, 0, 0], dtype=int8)
    uncertainty_type1 = array([3, 3, 1, 2, 2], dtype=int8)
    uncertainty_type2 = array([3, 3, 1, 2, 2], dtype=int8)
    if sensor_1_name == -1:
        w_matrix_use1 = array([0], dtype=int8)
        w_matrix_use2 = array([1, 1, 0, 0, 0], dtype=int8)
        uncertainty_vector_use1 = array([0], dtype=int8)
        uncertainty_vector_use2 = array([1, 2, 0, 0, 0], dtype=int8)
        uncertainty_type1 = array([1], dtype=int8)
        uncertainty_type2 = array([3, 3, 1, 2, 2], dtype=int8)

    if X2.shape[1] == 4:
        w_matrix_use1 = array([1, 1, 0, 0], dtype=int8)
        w_matrix_use2 = array([2, 2, 0, 0], dtype=int8)
        uncertainty_vector_use1 = array([1, 2, 0, 0], dtype=int8)
        uncertainty_vector_use2 = array([3, 4, 0, 0], dtype=int8)
        uncertainty_type1 = array([3, 3, 1, 1], dtype=int8)
        uncertainty_type2 = array([3, 3, 1, 1], dtype=int8)
        if sensor_1_name == -1:
            w_matrix_use1 = array([0], dtype=int8)
            w_matrix_use2 = array([1, 1, 0, 0], dtype=int8)
            uncertainty_vector_use1 = array([0], dtype=int8)
            uncertainty_vector_use2 = array([1, 2, 0, 0], dtype=int8)
            uncertainty_type1 = array([1], dtype=int8)
            uncertainty_type2 = array([3, 3, 1, 1], dtype=int8)

    # 3. Update file to include W matrix variables
    print "Writing to new file:", output_file_path

    # a. Update existing file to comply with new specification
    write_input_file(output_file_path,
                     X1, X2,
                     Ur1, Ur2, Us1, Us2, uncertainty_type1, uncertainty_type2,
                     K[valid_averages], Kr[valid_averages], Ks[valid_averages],
                     time_sensor_1[valid_averages], time_sensor_2[valid_averages],
                     sensor_1_name, sensor_2_name)

    # b. Add w matrix variables to updated file
    append_W_to_input_file(output_file_path,
                           w_matrix_val, w_matrix_row, w_matrix_col, w_matrix_nnz,
                           uncertainty_vector_row_count, uncertainty_vector,
                           w_matrix_use1, w_matrix_use2, uncertainty_vector_use1, uncertainty_vector_use2)

    # 4. Test harmonisation
    test_input_file(output_file_path)

    print "Done"
    return 0

if __name__ == "__main__":
    main(argv[1], argv[2])



