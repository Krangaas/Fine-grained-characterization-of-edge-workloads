import subprocess as sp
import os
import argparse


def main(args):
    N = args.n
    stress_args = ['stress-ng', '--job', "../"+args.job]

    if args.e == ['a']:
        events = ['-a']
    else:
        events = []
        for e in args.e:
            events.append("-e")
            events.append(e)

    # papiex separator, tells papiex to terminate option processing and pass the rest of the commands to the underlying shell
    events.append("--")

    runargs = ["papiex", "--csv", "-f", ""]
    runargs.extend(events)
    runargs.extend(stress_args)

    if os.path.isdir(args.o):
        print("Directory '%s' already exists. Please specify another directory name." %args.o)
        exit(0)
    os.mkdir(args.o)
    for i in range(N):
        runargs[3] = "stat." + args.o + "_%s" %(i+1)
        print(runargs)
        proc = sp.Popen(runargs, cwd=args.o)
        proc.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Profile a stress-ng method \
                                                  N times in sequence with papiex')
    parser.add_argument('-n', type=int, default=20,
                    help='number of times to profile. Default is 20')
    parser.add_argument('-o', metavar='O', type=str, required=True,
                    help='output directory filename prefix. Output will be of the form: "rawdata_<O>/stat.<O>_<iteration>"')
    parser.add_argument('-e', nargs='+', metavar='E', type=str, default=['a'],
                    help='list of PAPI hardware events to measure. Default is "a" (automatic)')
    parser.add_argument('--job', metavar='jobfile', type=str, required=True,
                    help='stress-ng jobfile.')
    args = parser.parse_args()
    main(args)
