# Fine-grained characterization of edge workloads

## Dependencies
- Python 3.10.6: https://www.python.org/downloads/
- PAPI: https://icl.utk.edu/papi/docs/index.html
- PapiEx: https://bitbucket.org/minimalmetrics/papiex-oss/src/master/
- stress-ng: https://github.com/ColinIanKing/stress-ng

## How to run
Follow the PapiEx README to set the environment.
- Run tests by running the script `run_tests.py`.
- Aggregate the data by running the script `aggregate_data.py`.
- Visualize the data in various modes, or perform classification by running the script `visualization.py`

More detailed information on running the scripts can be found by reading the helptext `--help` for each script.

## A basic example
The following command:
```
python3 run_tests.py -n 1 -o matprod -e PAPI_TOT_CYC PAPI_TOT_INS --job jobfiles/CPU/CPU_matprod
```
Will run stress-ng with the configuration provided in the *CPU_matprod* jobfile 1 time. During runtime, PapiEx monitors the hardware events *PAPI_TOT_INS* and *PAPI_TOT_CYC*. The output files will be stored in the directory *matprod*.

Running the command:
```
python3 aggregate_data.py -i matprod/* -o matprod
```
Will aggregate the data in the *matprod* directory to a new file *data_matprod.csv*.

Running the command:
```
python3 visualization --mode stats -i data_matprod.csv
```
Will print various statistical metrics about the dataset.

## An advanced example
Assuming several aggregated datasets exist in some directory *aggregated_data/*, running the following command:
```
python3 visualization --mode logbox -i aggregated_data/*
```
Will plot the datasets logarithmically along each attribute axis using a box plot.
