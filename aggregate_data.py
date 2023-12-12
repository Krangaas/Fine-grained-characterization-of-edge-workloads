import glob
import numpy as np
import argparse
from argparse import RawTextHelpFormatter
from script_utils import *


def fetch_leaves(c):
    """
    Function to parse collected thread value list and fetch leaf processes.
    Stress-ng will spawn a given number of processes that performs some work depending on the chosen stress method.

    For some stress-ng vm stress methods, such as 'read64', stress-ng will spawn processes that spawn another set of leaf-processes.
    The method will first try to fetch processes with unique parent process ids, these are the leaf processes that are doing the actual work.

    If all leaf-processes originate from the same parent process there will be only one unique parent process id, and so all processes are leaves.


    It is also possible that a set of processes are spawned which spawns another set, but all processes perform actual work.
    This method, however, is currently unable to properly aggregate data for this scenario,
    as it will only keep the leaf-processes even though the branch-processes do work as well.
    So take care!

    Returns filtered set of leaf-processes.
    """
    # get count of all parent process ids
    parent_process_ids, count = np.unique(
        [p["Parent process id"] for p in c], return_counts=True)

    # ignore child process id with *lowest number parent process id*,
    # as the function of this process is to spawn the processes that do the actual work
    grandparent_id_idx = parent_process_ids.argmin()
    parent_process_ids = np.delete(parent_process_ids, grandparent_id_idx)
    count = np.delete(count, grandparent_id_idx)

    if len(parent_process_ids) > 1:
        # if there are more than one parent process ids,
        # fetch all unique parent process ids
        unique_ids = [id for idx, id in enumerate(parent_process_ids) if count[idx] == 1]
        # for each unique parent process id, fetch dictionary associated with its child process
        leaf_data = [d for d in c if d["Parent process id"] in unique_ids]
        return leaf_data

    elif len(parent_process_ids) == 1:
        # all leaf processes originate from the same parent process, fetch these dictionaries
        leaf_data = [d for d in c if d["Parent process id"] in parent_process_ids]
        return leaf_data
    else:
        print("Something went wrong...")
        exit(0)


def main(args):
    if not isinstance(args.i, list):
        dirpath = glob.glob(args.i)
    else:
        dirpath = []
        for d in args.i:
            dirpath.append(d)


    # append .csv postfix to filename if none was given
    if args.o.endswith(".csv"):
        filename = "data_" + args.o
    else:
        filename = "data_" + args.o + ".csv"


    # make sure that only the header of the first dataset gets written
    first = True

    if args.mode == "ppx":
        for dir in dirpath:
            full_data, field_names = open_papiex_results_dir(dir + "/*")
            leaf_data = fetch_leaves(full_data)
            save_as_aggregated_csv(leaf_data, field_names, filename, first)
            first = False

    elif args.mode == "agg":
        collection = []
        for file in dirpath:
            d, header = open_aggregated_csv(file)
            collection.append(d)
        arguments = "--job"
        for c in collection:
            arguments += " " + c[0]["Arguments"].split()[1].removeprefix("../jobfiles/")
        collection[0][0]["Arguments"] = arguments
        for data in collection:
            save_as_aggregated_csv(data, header, filename, first)
            first = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Aggregate csv data files to a single file', formatter_class=RawTextHelpFormatter)
    parser.add_argument('-i', nargs='+', metavar='I', required=True, type=str,
                        help='Specify directory of data files to aggregate, can be a wildcard (EX: "matrixprod/*").')
    parser.add_argument('-o', metavar='O', required=True,
                        help='Output file name, will be of the form: "data_<O>.csv.')
    parser.add_argument('--mode', metavar='m', type=str, default='ppx',
                        help='specify what type of data to aggregate, default is "ppx".\
                        \nValid arguments are ["ppx" (papiex), "agg" (aggregated)]\
                        \n\n"ppx" mode will aggregate data of the structure:\
                              \n. \
                              \n└── parent_directory\
                              \n    └── sub_directory\
                              \n        └── data.csv\
                        \nThis is how the script "run_tests.py" orders the data collected by PAPIEX.\
                        \n\n"agg" mode will aggregate data of the structure:\
                              \n. \
                              \n└── parent_directory\
                              \n    └── data.csv\
                        \nThis option is used to gather several aggregated datasets to one CSV file.')

    args = parser.parse_args()

    main(args)
