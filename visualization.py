import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import argparse
import statistics as st
from script_utils import *
import glob


class SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)


zero_val = ["[PROCESS] Memory locked (at exit) KB"]
# zero variance
zero_var = [
    "[PROCESS] Memory library (at exit) KB",
    "[PROCESS] Memory text (at exit) KB"]

# real time reliant
realtime= [
    "[PROCESS] Wallclock usecs",
    "Real cycles",
    "Real usecs"]

perf_corr = [
    # perf corr with l1_icm
    "PAPI_L2_ICA",
    # perf corr with virtual cycles
    "Virtual usecs"]

various = [
    # Varies discretly between (460) 464 and 468 "randomly"
    "[PROCESS] Memory stack (at exit) KB"]

corr = [
    #corr with tot ins
    "PAPI_BR_CN",
    "PAPI_BR_INS",
    "PAPI_BR_MSP",
    "PAPI_FUL_ICY",
    "PAPI_LD_INS",
    "PAPI_LST_INS",
    "PAPI_RES_STL",
    "PAPI_SR_INS",
    "PAPI_TOT_CYC"

    # corr with l1 dcm
    "PAPI_L2_DCA",
    "PAPI_L2_DCM",
    "PAPI_TLB_DM",
    "[PROCESS] Memory resident max KB",

    # corr with l1 icm
    #"PAPI_L2_ICA",
    "PAPI_L2_ICM",
    "PAPI_TLB_IM",

    # negative corr with mem shared
    "[PROCESS] Memory heap (at exit) KB"]


def scrub_data(data, scrublist, scrub_attributes=True, add_scrub=None):
    out = []
    if add_scrub:
        if isinstance(add_scrub, list):
            scrublist.extend(add_scrub)
        if isinstance(add_scrub, str):
            scrublist.append(add_scrub)

    if scrub_attributes:
        print(scrublist)
    for entry in data:
        tmp = entry.copy()
        for key, value in entry.items():
            # remove metadata
            if not isinstance(value, list):
                del tmp[key]
            # remove redundant data
            elif scrub_attributes and key in scrublist:
                del tmp[key]
            # Shorten some field names
            elif "[PROCESS] " in key:
                new_key = key.replace("[PROCESS] ", "")
                tmp[new_key] = tmp.pop(key)

        out.append(tmp)
    # gather keys
    scrubbed_field_names = list(out[0].keys())
    return out, scrubbed_field_names

def parse_data(filenames, scrub_level=0, add_scrub=None):
    data = []
    scrublist = []
    for file in filenames:
            d, field_names = open_papiex_csv(file, aggregated=True)
            data.append(d)

    if scrub_level == 0: # Retain all data
        return data, field_names

    elif scrub_level == 1: # Remove metadata and zero value data
        scrublist.extend(zero_val)
        return scrub_data(data, scrublist, scrub_attributes=True, add_scrub=add_scrub)

    elif scrub_level == 2: # Remove metadata and redundant fields
        scrublist.extend(zero_val)
        scrublist.extend(zero_var)
        scrublist.extend(various)
        scrublist.extend(perf_corr)
        scrublist.extend(realtime)
        return scrub_data(data, scrublist, scrub_attributes=True, add_scrub=add_scrub)
    else:
        return data, field_names

def parse_filepath(path):
    if path == None:
        return None
    if isinstance(path, str):
        filepaths = glob.glob(path)
    else:
        filepaths = path

    return filepaths


def get_matrix(data, field_names):
    '''
    Fetch all performance counter values from the list of datasets,
    Return np.array with dims (<number of data points>, <Number of counters>)
    '''
    # Create a new list with N rows
    matrix = [[] for _ in range(len(field_names))]

    # Iterate through the dictionaries
    for d in data:
        # Iterate through the keys
        for i, key in enumerate(field_names):
            # Append the values corresponding to the key in the new_list at the row i
            matrix[i].extend(d[key])
    return np.array(matrix).T

def calc_median(data):
    median_data = []
    for i in range(len(data)):
        tmp = []
        for _, val in data[i].items():
            if isinstance(val, list):
                tmp.append(st.median(val))
        median_data.append(tmp)

    return np.array(median_data)

def calc_euc_dist(arr1, arr2):
    dist = np.linalg.norm(arr1 - arr2)
    return dist

def calc_cos_angle(arr1, arr2):
    angle = ( np.dot(arr1, arr2) ) / ( np.linalg.norm(arr1) * np.linalg.norm(arr2) )
    return angle[0]


def classify(data, ukn_data, class_names, ukn_name):
    '''
    Classify an unkown dataset given a set of class representatives

    The method assumes that the median of each class dataset and the unknown dataset are good representatives.
    The Cosine Angle and Euclidean Distance are then found from the unknown median vector to each class median vector.
    The Closeness Percentage, which is the ratio of the total Euclidean Distance between the unknown median vector and each class median vector,
    is then calculated.

    Returns a list of dictionaries that each contain distance metrics and metadata, and a CSV header list
    '''

    output_field_names = ["Name", "Class", "Cosine similarity",
                   "Euclidean distance", "Closeness Percentage"]

    median_data = calc_median(data)
    ukn_data = calc_median([ukn_data])

    res = []
    distances = []
    for i in range(len(median_data)):
        cos_angle = calc_cos_angle(ukn_data, median_data[i])
        euc_dist = calc_euc_dist(ukn_data, median_data[i])
        distances.append(euc_dist)
        res.append({"Name":ukn_name, "Class":class_names[i],
                    "Cosine similarity":cos_angle,
                    "Euclidean distance":euc_dist})


    # Calculate the closeness percentage for each class median
    closeness_pct = [(100 / distance) for distance in distances]
    # normalize the percentages
    total_pct = sum(closeness_pct)
    closeness_pct = [(pct / total_pct) * 100 for pct in closeness_pct]
    for i in range(len(res)):
        res[i]["Closeness Percentage"] = closeness_pct[i]

    return res, output_field_names

def boxplot_per_field(data, field_names, filenames, ncols=6, yscale='linear'):
    nrows = len(field_names) // ncols + (len(field_names) % ncols > 0)
    fig, axs = plt.subplots(nrows=nrows, ncols=ncols, sharex=True)

    for name, field, ax in zip(field_names, field_names, axs.flat):
        values = []
        file_names= []

        # gather data
        for i, f in enumerate(filenames):
            values.append(data[i][field])
            file_names.append(f)

        # create plot, add title, add grid
        bplot = ax.boxplot(values, patch_artist=True)
        ax.set_yscale(yscale)
        ax.set_title(name, fontsize=10)
        if yscale == 'linear':
            ax.ticklabel_format(axis='y', style='sci', scilimits=[-3, 3])
        ax.grid()

        # set color
        ax.set_xticks([i+1 for i in range(len(file_names))], file_names, fontsize=7.8, rotation=90)
    plt.show()

def stats(data, field_names):
    # parse and scrub datasets

    matrix = get_matrix(data, field_names)
    df = pd.DataFrame(matrix, columns=field_names)

    print("Variance")
    print(df.var())

    c = df.corr(method='spearman')
    sns.heatmap(c,
        xticklabels=c.columns,
        yticklabels=c.columns, annot=True)
    plt.show()

def compare_rawdata_mode(data, ukn_data, ukn_names, class_names):
    for i in range(len(ukn_data)):
        res, output_field_names = classify(data, ukn_data[i], class_names, ukn_names[i])
        filename_new = "similiarities_%s.csv" %(ukn_names[i])
        save_csv_from_dict(res, output_field_names, filename_new)


def main(args):
    # parse filepaths
    filenames = parse_filepath(args.i)

    wload_names = []
    # strip pre- and postfix from workload names
    for f in filenames:
        for s in f.split("/"):
            if ".csv" in s:
                for ss in s.split("_"):
                    if ".csv" in ss:
                        wload_names.append(ss.removesuffix(".csv"))

    ukn_names = []
    ukn_filenames = parse_filepath(args.o)
    if ukn_filenames is not None:
        for f in ukn_filenames:
            for s in f.split("/"):
                if ".csv" in s:
                    for ss in s.split("_"):
                        if ".csv" in ss:
                            ukn_names.append(ss.removesuffix(".csv"))


    if args.mode == "box":
        data, field_names = parse_data(filenames, scrub_level=2)
        boxplot_per_field(data, field_names, wload_names)

    elif args.mode == "logbox":
        data, field_names = parse_data(filenames, scrub_level=2)
        boxplot_per_field(data, field_names, wload_names, yscale='log')

    elif args.mode == "stats":
        data, field_names = parse_data(filenames, scrub_level=1)
        stats(data, field_names)

    elif args.mode == "cmp-raw":
        data, field_names = parse_data(filenames, scrub_level=2)
        ukn_data, _ = parse_data(ukn_filenames, scrub_level=2)

        compare_rawdata_mode(data, ukn_data, ukn_names, wload_names)

    else:
        print("No such option:", args.mode)
        exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Visualize data.', formatter_class=SmartFormatter)
    parser.add_argument('-i', nargs='+', metavar='I', type=str, default="collected_classes/*",
                    help='Specify class data file directories, can be a wildcard. Default is "collected_classes/*"')
    parser.add_argument('-o', nargs='+', metavar='O', type=str, default=None,
                    help='CSV file containing an unclassified dataset. Required for "cmp-raw" or "cmp-ct" mode. \
                        Output will inherit the name of the file.')
    parser.add_argument('--mode', metavar='m', type=str, default='cmp-raw',
                        help='R|Data visualizing/processing mode. Default is "cmp-raw". \
                        \nValid arguments are:\
                        \n  -"cmp-raw" (compare rawdata) \
                        \n  -"box" (boxplot) \
                        \n  -"logbox" (logarithmic boxplot) \
                        \n  -"stats":  (find variance, correlations)')
    parser.add_argument('-f', metavar='f', type=str, default=None,
                        help='Output filename (Optional). Only used for "centroid" (ct), and "summary" mode.\
                            File name will be of the form: "<mode>_<f>.csv')
    args = parser.parse_args()

    if "cmp" in args.mode and not args.o:
        print("No unknown datset given for comparison mode, defaulting to boxplot mode")
        args.mode = "box"

    main(args)
