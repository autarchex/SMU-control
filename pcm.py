#!/usr/bin/env python
#
#PCM (pulse code modulation) script to dump a list of voltages to SMU.
#Roop 20170622

import sys, argparse, logging
from os import listdir
from instruments import B2901A      #instruments.py


# Gather our code in a main() function
def main(args, loglevel):
    logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)

    devices = listdir("/dev/")           #get listing of contents of /dev directory
    usbtmcdevices = list(s for s in devices if "usbtmc" in s)  #list all usbtmc* filenames in /dev

    if len(usbtmcdevices) < 1:
        logging.info("No USB TMC devices found; exiting.")
        return
    logging.debug("Found:" + str(usbtmcdevices))
    devicepath = "/dev/" + usbtmcdevices[0] #select first available match
    logging.debug("Selecting:" + str(devicepath))

    smu = B2901A(devicepath)
    smu.reset()

    lineNumber = 0
    for line in args.infile.readlines():
        lineNumber = lineNumber + 1
        values = ''.join(line.split()).split(',')    #remove whitespace, split on commas
        if len(values) < 2:             #must have at least time and one voltage
            if lineNumber == 1:
                logging.info("Error: PCM input requires period and at least one value.")
                logging.debug("Input values: " + str(values))
                return
            else:
                logging.debug("Terminating on input line " + str(lineNumber) + ": insufficient input.")
                logging.debug("Line " + str(lineNumber) + " values: " + str(values))
                break

        tstep = float(values[0])          #first value is timebase
        logging.debug("Line " + str(lineNumber) + ": tstep= " + str(tstep))
        voltage_list = [float(s) for s in values[1:]]  #others are voltages
        logging.debug("Line " + str(lineNumber) + ": vlist= " + str(voltage_list))

        smu.performVoltageListSweep(voltage_list, tstep, compliance=0.1)
    logging.info("Processed " + str(lineNumber) + " lines of input.")

    smu.enableOutput(False)



# Process arguments on command line and execute main()
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description = "Sends PCM data to a B2901A SMU.",
        epilog = "Expected PCM file format is a comma-separated list of \
                  numerical data in text format, terminated with a newline \
                  character. The first value is the sample period, in seconds. \
                  Subsequent values are output levels, in volts."
        )
    # TODO Specify your real parameters here.
    parser.add_argument( "infile",
        nargs='?', type=argparse.FileType('r'), default=sys.stdin,
        help="Input PCM file (or standard input if ommitted)",
        metavar = "input file")

    parser.add_argument( "--verbose", "-v",
        help="increase output verbosity",
        action="store_true")
    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
    #run main function
    main(args, loglevel)
