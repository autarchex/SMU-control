#!/usr/bin/env python
#
#PCM (pulse code modulation) script to dump a list of voltages to SMU.
#Roop 20170622

import sys, argparse, logging
from os import listdir
from decimal import Decimal
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
    repeat = 0
    timeVoltagePairs = []
    for line in args.infile.readlines():
        lineNumber = lineNumber + 1
        linevalues = line.split()    #remove whitespace, split on commas
        if len(linevalues) < 2:             #must have at least two items
            logging.debug("Skipped input line " + str(lineNumber) + ", insufficient input: " + str(linevalues))
            continue
        if 'R' in linevalues[0]:                    #look for R followed by a number
            repeat = int(linevalues[1])             #this signifies a waveform repeat
            logging.debug("Found repeat instruction, R= " + str(repeat) + " on line " + str(lineNumber))
            continue
        timeVoltagePairs.append([Decimal(linevalues[0]), Decimal(linevalues[1])])    #save pair
    logging.info("Processed " + str(lineNumber) + " lines of input.")

    #Assemble waveform as list of voltages using one common timebase
    tstep = findCommonTimeStep(timeVoltagePairs)    #find common timebase
    logging.info("Using timebase of " + str(tstep) + " s.")
    voltage_list = []
    for [t,v] in timeVoltagePairs:
        copies = int(t / tstep)     #should always be an even division
        for n in range(copies):
            voltage_list.append(v)  #duplicate v in list appropriate number or times for this timebase
    logging.debug("voltage_list follows:")
    logging.debug(str(voltage_list))

    #Execute sweep on instrument once, then repeat correct number of times.
    logging.info("Executing sweep 1 of " + str(repeat + 1))
    smu.performVoltageListSweep(voltage_list, tstep, compliance=0.1)
    for n in range(repeat):
        logging.info("Executing sweep " + str(n+1) + " of " + str(repeat + 1))
        smu.initiate()          #repeat last sweep operation with same settings
    logging.info("Done.")
    smu.enableOutput(False)


def findCommonTimeStep(tv):
    """Takes list of time,value Decimal pairs. Returns a time step which is the
    largest time step that can be used to exactly represent all of the pairs in
    the input list."""
    import functools        #needed for reduce()
    def gcd(a,b):           #greatest common denominator of 2 integers
        while b:
            a,b = b, a % b
        return a
    def lcm(a,b):           #least common multiple of two integers
        return a * b // gcd(a,b)
    def lcmm(arglist):      #least common multiple of a list of integers
        return functools.reduce(lcm, arglist)
    times = [t for [t,v] in tv]     #extract list of times
    denominators = [t.as_integer_ratio()[1] for t in times]     #get integer representation denominator of each
    logging.debug("Denominators: " + str(denominators))
    lcm_denom = lcmm(denominators) #LCM of list of denominators
    tstep = Decimal('1') / Decimal(lcm_denom)
    return tstep



# Process arguments on command line and execute main()
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description = "Sends PCM data to a B2901A SMU.",
        epilog = "Expected input format is a comma-separated or space-separated \
                  list of symbol pairs, one pair per line.  If the first symbol \
                  is a number, it is a time in seconds and the second symbol is \
                  a voltage.  If the first symbol is 'R', the second symbol is \
                  a number of repetitions to apply to the waveform. "
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
