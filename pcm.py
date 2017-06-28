#!/usr/bin/env python
#
#PCM (pulse code modulation) script to dump a list of voltages to SMU.
#Roop 20170626
#REQUIRES Python 3.6 or later

import sys, argparse, logging
import time
from os import listdir
from decimal import Decimal
from instruments import B2901A      #instruments.py


# Gather our code in a main() function
def main(args, loglevel):
    logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)

    devices = listdir("/dev/")                                 #get listing of contents of /dev directory
    usbtmcdevices = list(s for s in devices if "usbtmc" in s)  #list all usbtmc* filenames in /dev
    if args.mock:
        print("Using MOCK device!")
    if not args.mock and len(usbtmcdevices) < 1:
        print("No USB TMC devices found; exiting.")
        return
    logging.debug("Found:" + str(usbtmcdevices))
    if args.mock:
        dev = ""
    else:
        dev = usbtmcdevices[0]
    devicepath = "/dev/" + dev                                  #select first available match
    logging.debug("Selecting:" + str(devicepath))

    smu = B2901A(devicepath, mock=args.mock)                    #connect to SMU and reset it
    smu.reset()

    #Parse input file line by line.
    #DEF n opens a new waveform n.  OUT <ON/OFF> controls output state.
    #W n m plays waveform #n, m times.  A pair of numbers on a line is interpreted
    #as [time, voltage] and added to the currently open waveform.
    waveforms = {}                                                                  #stores waveforms
    currentWaveform = 0
    waveforms[currentWaveform] = Waveform(currentWaveform)                          #create first waveform and store it
    replay = []                                                                     #tracks play operations previously performed
    ln = 0                                                                          #line number
    print("---------------------------")
    for line in args.infile.readlines():
        ln = ln + 1
        tokens = line.split()                                                       #split on whitespace
        if len(tokens) < 2:                                                         #skip blank lines and single-symbols
            logging.debug("Skipped input line " + str(ln) + ", insufficient input: " + str(tokens))
            continue
        if tokens[0][0] == '#' or tokens[1][0] == '#':                                                     #skip comments
            continue
        if is_number(tokens[0]):                                                    #waveform data?
            if not is_number(tokens[1]):                                            #second parameter isn't a number also
                print("Error - non-numeric data on line " + str(ln))
                continue
            t = Decimal(tokens[0])                                                  #import as Decimal to preserve precision
            v = Decimal(tokens[1])
            waveforms[currentWaveform].addPoint(t,v)                                #add datapoint to the currently open waveform

        else:                                                                       #not waveform data, must be an operation
            op = tokens[0]
            if op == 'D' or op == 'DEF':                                            #Define-waveform operation
                if not is_number(tokens[1]):                                        #Can't process a DEF with no ID number
                    print("Error - waveform definition without ID on line " + str(ln))
                    continue
                idnum = int(tokens[1])
                if idnum < 0:
                    print("Error - waveform definition with negative ID on line " + str(ln))
                    continue
                waveforms[idnum] = Waveform(idnum)                                  #create and store a new waveform object
                currentWaveform = idnum                                             #remember its location
                logging.debug("Defined waveform " + str(idnum))
                continue

            if op == 'OUT' or op == 'out':                                          #output control
                if tokens[1] == 'ON' or tokens[1] == 'on':
                    smu.enableOutput(True)
                elif tokens[1] == 'OFF' or tokens[1] == 'off':
                    smu.enableOutput(False)
                continue

            if op == 'W' or op == 'w':                                              #waveform play command
                if not is_number(tokens[1]):                                        #missing or non-numeric id number?
                    print("Error - waveform operation missing ID on line " + str(ln))
                    continue
                idnum = int(tokens[1])
                if idnum < 0 or idnum not in waveforms.keys():
                    print("Error - waveform requested does not exist, on line " + str(ln))
                    continue
                wf = waveforms[idnum]                                               #select the waveform to play
                plays = 1
                if len(tokens) > 2 and is_number(tokens[2]):                        #additional parameter present?
                    plays = int(tokens[2])                                          #it is number of iterations
                    if plays < 1:
                        plays = 1
                playWaveform(wf, smu, iterations=plays)
                replay.append(['W',wf,plays])                                       #save a record for possible replay later
                continue

            if op == 'R' or op == 'r':                                              #replay command
                if not is_number(tokens[1]) or int(tokens[1]) < 1:                  #parameter is number of iterations
                    print("Error - unusable replay count found on line " + str(ln))
                    continue
                repeats = int(tokens[1])
                print("---------------------------")
                print("Found REPLAY on line " + str(ln) + "; replaying " + str(len(replay)) + " operations, " + str(repeats) + " times.")
                for n in range(repeats):
                    for r in replay:
                        if r[0] == 'W':                                             #entry describes a waveform play operation
                            wf = r[1]
                            iterations = r[2]
                            playWaveform(wf, smu, iterations)                       #replay the waveform
                    print("---------------------------")
                for n in range(repeats):
                    replay.extend(replay)                                           #record the replay operation itself for possible replay later

    print("Processed " + str(ln) + " input lines.")

    # END

def playWaveform(wf, smu, iterations=1):
    """Play a waveform one or more times."""
    smu.prepareVoltageListSweep(wf.vlist, wf.tstep, compliance=0.1)                 #prepare SMU for list sweep
    print("Loaded waveform " + str(wf.id) + "; queuing " + str(iterations) + " sweeps.")
    for n in range(iterations):
        smu.initiate()                                                              #execute sweep on instrument
    playtime = float(wf.duration) * iterations * 0.99                               #estimate total sweep duration, minus a hair
    print("Waiting " + str(playtime) + " seconds.")
    time.sleep(playtime)


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
        self.duration = 0
        pass

    def addPoint(self, time, voltage):
        """Add a duration (seconds) and level (volts)"""
        self.points.append([time,voltage])                      #add recent point
        self.tstep = self.findCommonTimeStep(self.points)       #calculate new timebase
        vlist = []
        for [t,v] in self.points:
            copies = int(t / self.tstep)                        #number of repetitions needed
            for n in range(copies):
                vlist.append(v)                                 #add that number of copies of voltage
        self.vlist = vlist                                      #save result
        self.duration = len(self.vlist) * self.tstep            #calculate total play time

    def findCommonTimeStep(self, tv):
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

    parser.add_argument( "--mock", "-m",
        help="Use mock instrument. Note: does not reply to requests!",
        action="store_true")

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
    #run main function
    main(args, loglevel)
