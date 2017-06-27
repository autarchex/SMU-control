#!/usr/bin/env python
#
#PCM (pulse code modulation) script to dump a list of voltages to SMU.
#Roop 20170626
#REQUIRES Python 3.6 or later

import sys, argparse, logging
from os import listdir
from decimal import Decimal
from instruments import B2901A      #instruments.py


# Gather our code in a main() function
def main(args, loglevel):
    logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)

    devices = listdir("/dev/")                                 #get listing of contents of /dev directory
    usbtmcdevices = list(s for s in devices if "usbtmc" in s)  #list all usbtmc* filenames in /dev

    if len(usbtmcdevices) < 1:
        logging.info("No USB TMC devices found; exiting.")
        return
    logging.debug("Found:" + str(usbtmcdevices))
    devicepath = "/dev/" + usbtmcdevices[0]                     #select first available match
    logging.debug("Selecting:" + str(devicepath))

    smu = B2901A(devicepath)
    smu.reset()

    waveforms = []                                              #stores waveforms
    currentWaveform = ''
    defining = False                                            #are we currently defining a waveform?

    #Step through the input file looking only for waveform definitions, process them.
    #Definitions start with a line "DEF n", n being waveform number; consist of lines of t,v pairs;
    #they end with END.
    ln = 0                                                      #line number
    for line in args.infile.readlines():
        ln = ln + 1
        linevalues = line.split()                               #remove and split on whitespace
        if len(linevalues) < 2:
            if linevalues[0] == 'END':
                defining = False                                #done with current waveform
            else:
                logging.debug("Skipped input line " + str(lineNumber) + ", insufficient input: " + str(linevalues))
            continue
        if linevalues[0] == 'D' or linevalues[0] == 'DEF':      #a waveform definition start
            if linevalues[1] is None:
                logging.debug("Error - waveform definition without ID on line " + str(ln))
            else:
                idnum = linevalues[1]
                currentWaveform = Waveform(idnum)
                waveforms.append(currentWaveform)
                defining = True
            continue
        if is_number(linevalues[0] and is_number(linevalues[1]):    #a point entry
            t = Decimal(linevalues[0])
            v = Decimal(linevalues[1])
            currentWaveform.addPoint(t,v)
            continue

    logging.info("Processed " + str(lineNumber) + " lines of input.")
    logging.info("Defined " + str(len(waveforms)) + " waveforms.")


    #Step through input file ignoring waveform definitions, process operations.
    #Operations include "W n m", which plays waveform n m times; "OUT <ON/OFF>" which enables/disables output.
    ln = 0                                                      #line number
    for line in args.infile.readlines():
        ln = ln + 1
        linevalues = line.split()                               #remove and split on whitespace
        if len(linevalues) < 2:                                 #there are no single-symbol operations
            continue
        if is_number(linevalues[0]):                            #operations bigin with a word, not numbers
            continue
        op = linevalues[0]
        if op == 'D' or op == 'DEF':                            #ignore the DEFine waveform command, already Done
            continue
        if op == 'OUT' or 'out':                                #output control
            if linevalues[1] == 'ON' or linevalues[1] == 'on':
                smu.enableOutput(True)
            elif linevalues[1] == 'OFF' or linevalues[1] == 'off':
                smu.enableOutput(False)
            continue
        if op == 'W' or 'w':                                    #waveform play command
            idnum = linevalues[1]
            plays = 1
            if len(linevalues) > 2:                             #additional argument?
                if is_number(linevalues[2]):                    #AND it is a number?
                    plays = int(linevalues[2])                  #it is number of iterations
                    if plays < 1:
                        plays = 1
            wf = None
            for w in waveforms:
                if w.id == idnum:                               #find correct waveform
                    wf = w
            if wf is None:                                      #failed to find it!
                logging.info("Error: requested play of waveform " + str(idnum) + " but waveform not found!")
                continue
            logging.info("Executing sweep 1 of " + str(plays) + "of waveform " + str(idnum))
            smu.performVoltageListSweep(wf.vlist, wf.tstep, compliance=0.1)
            for n in range(plays-1):
                logging.info("Executing sweep " + str(n+2) + " of " + str(plays) + "of waveform " + str(idnum))
                smu.initiate()
    logging.info("Done.")


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


class Waveform:
    """Represents one playable waveform on the SMU."""
    def __init__(self, num):
        self.id = num
        self.points = []
        self.vlist = []
        pass

    def addPoint(self, time, voltage):
        """Add a duration (seconds) and level (volts)"""
        self.points.append([time,voltage])                      #add recent point
        self.tstep = self.findCommonTimeStep(self.points)       #calculate new timebase
        vlist = []
        for [t,v] in self.points:
            copies = t // self.tstep                            #number of repetitions needed
            for n in range(copies):
                vlist.append(v)                                 #add that number of copies of voltage
        self.vlist = vlist                                      #save result

    def findCommonTimeStep(tv):
        """Takes list of time,value Decimal pairs. Returns a time step which is the
        largest time step that can be used to exactly represent all of the pairs in
        the input list."""
        import functools                                             #needed for reduce()
        def gcd(a,b):                                               #greatest common denominator of 2 integers
            while b:
                a,b = b, a % b
            return a
        def lcm(a,b):                                               #least common multiple of two integers
            return a * b // gcd(a,b)
        def lcmm(arglist):                                          #least common multiple of a list of integers
            return functools.reduce(lcm, arglist)
        times = [t for [t,v] in tv]                                 #extract list of times
        denominators = [t.as_integer_ratio()[1] for t in times]     #get integer representation denominator of each
        lcm_denom = lcmm(denominators)                              #LCM of list of denominators
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
    # add argument processors
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
