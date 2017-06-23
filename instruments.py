import os
import fcntl
import time
#These modules from https://github.com/olavmrk/python-ioctl
#import ioctl
#import ioctl.linux


"""This file contains control classes for USB Test & Measurement Class
(USBTMC) instruments and a simplistic interface to the kernel USBTMC driver.
Use it however you like."""

class ioc:
    """For translating C ioctl constants to Python."""
    import struct
    def __init__(self):
        # constant for linux portability
        self._IOC_NRBITS = 8
        self._IOC_TYPEBITS = 8
        # next two are architecture specific
        self._IOC_SIZEBITS = 14
        self._IOC_DIRBITS = 2
        self._IOC_NRMASK = (1 << self._IOC_NRBITS) - 1
        self._IOC_TYPEMASK = (1 << self._IOC_TYPEBITS) - 1
        self._IOC_SIZEMASK = (1 << self._IOC_SIZEBITS) - 1
        self._IOC_DIRMASK = (1 << self._IOC_DIRBITS) - 1
        self._IOC_NRSHIFT = 0
        self._IOC_TYPESHIFT = self._IOC_NRSHIFT + self._IOC_NRBITS
        self._IOC_SIZESHIFT = self._IOC_TYPESHIFT + self._IOC_TYPEBITS
        self._IOC_DIRSHIFT = self._IOC_SIZESHIFT + self._IOC_SIZEBITS
        self._IOC_NONE = 0
        self._IOC_WRITE = 1
        self._IOC_READ = 2

    def _IOC(self, dir, type, nr, size):
        if isinstance(size, str):
            size = struct.calcsize(size)
        return dir  << self._IOC_DIRSHIFT  | \
               type << self._IOC_TYPESHIFT | \
               nr   << self._IOC_NRSHIFT   | \
               size << self._IOC_SIZESHIFT

    def _IO(self, type, nr):
        return self._IOC(self._IOC_NONE, type, nr, 0)
    def _IOR(self, type, nr, size):
        return self._IOC(self._IOC_READ, type, nr, size)
    def _IOW(self, type, nr, size):
        return self._IOC(self._IOC_WRITE, type, nr, size)
    def _IOWR(self, type, nr, size):
        return self._IOC(self._IOC_READ | self._IOC_WRITE, type, nr, size)


class Instrument:
    """Template class for generic USBTMC/USB488 instruments. Wraps USB-TMC
    (Test & Measurement Class) kernel driver. The kernel driver presents a file
    I/O interface.  Device needs to have already enumerated as a USB-TMC device
    to the system, i.e., should be a "/dev/usbtmc0" or similar present in /dev.
    Other specific instruments in this module inherit from this class.
    Instruments should speak SCPI / be IEEE 488.2 compliant."""
    def __init__(self, devicepath, description="USB TMC instrument"):
        """Argument 'device' (string) is path to /dev entry, typically /dev/usbtmc0 or /dev/usbtmc1"""
        self.devicepath = devicepath
        self.fd = os.open(devicepath, os.O_RDWR)
        self.ioc = ioc()        #helper object for ioctl constant calculations
        print("Connecting to " + description + " at " + devicepath)
        print("Requesting device to identify...")
        self.idn = self.identify()
        print("Device replied: \"" + self.idn + "\"")
        #extract manufacturer, model number, serial number, and revision number
        self.mfr, self.model, self.sn, self.version = self.idn.split(",")
        if self.expectedModel not in self.model:
            print("Warning: device returned model \'" + self.model + "\', expected \'" + self.expectedModel + "\'")

    #BASIC FILE I/O
    def read(self, length=4000):
        """Reads (text) from instrument.  Reads byte vector (file is binary),
        decodes into a string, strips leading/trailing whitespace and terminal newline"""
        return os.read(self.fd, length).decode().strip()

    def readb(self, length=4000):
        """reads without any conversion, so returns a byte vector."""
        return os.read(self.fd, length)

    def write(self, command):
        """Writes (text) to instrument. Adds a terminal newline and decodes to bytes,
        because file is open as binary, then sends it"""
        cmd = command + "\n"
        os.write(self.fd, cmd.encode());

    def writeb(self, command):
        """writes without any conversion, so sends a byte vector.  Will fail if given a string."""
        os.write(self.fd, command)

    def ask(self, command, length=4000):
        """combined write-read for commands that end in '?', for convenience."""
        self.write(command)
        return self.read(length)

    #IOCTL OPERATIONS
    #Commented lines below copied from tmc.h kernel header.
    #/* Request values for USBTMC driver's ioctl entry point */
    #define USBTMC_IOC_NR			91
    #define USBTMC_IOCTL_INDICATOR_PULSE	_IO(USBTMC_IOC_NR, 1)
    #define USBTMC_IOCTL_CLEAR		_IO(USBTMC_IOC_NR, 2)
    #define USBTMC_IOCTL_ABORT_BULK_OUT	_IO(USBTMC_IOC_NR, 3)
    #define USBTMC_IOCTL_ABORT_BULK_IN	_IO(USBTMC_IOC_NR, 4)
    #define USBTMC_IOCTL_CLEAR_OUT_HALT	_IO(USBTMC_IOC_NR, 6)
    #define USBTMC_IOCTL_CLEAR_IN_HALT	_IO(USBTMC_IOC_NR, 7)
    #define USBTMC488_IOCTL_GET_CAPS	_IOR(USBTMC_IOC_NR, 17, unsigned char)
    #define USBTMC488_IOCTL_READ_STB	_IOR(USBTMC_IOC_NR, 18, unsigned char)
    #define USBTMC488_IOCTL_REN_CONTROL	_IOW(USBTMC_IOC_NR, 19, unsigned char)
    #define USBTMC488_IOCTL_GOTO_LOCAL	_IO(USBTMC_IOC_NR, 20)
    #define USBTMC488_IOCTL_LOCAL_LOCKOUT	_IO(USBTMC_IOC_NR, 21)
    def pulse(self):
        """Request device to pulse an indicator on its front panel."""
        request = self.ioc._IO(91, 1)
        fcntl.ioctl(self.fd, request)

    def clear(self):
        """Issue a device-clear command."""
        request = self.ioc._IO(91, 2)
        fcntl.ioctl(self.fd, request)

    def readStatusByte(self):
        """Read status byte over sidechannel.  Non-blocking."""
        request = self.ioc._IOR(91, 18, 1)
        return fcntl.ioctl(self.fd, request, 1)

    #COMMON SCPI COMMANDS
    def identify(self):
        return self.ask("*IDN?", 300)

    def reset(self):
        self.write("*RST")

    def clearStatus(self):
        self.write("*CLS")

    def wait(self):
        """Issues a *WAI 'wait' command, which prohibits instrument from
        executing new commands until all pending commands have completed.  Does
        not block."""
        self.write("*WAI")

    def shortWaitForComplete(self):
        """This is a BLOCKING wait for previous operations to complete.  It is
        suitable for waiting on completion of reasonably short-duration (<2 sec)
        operations.  Using this method to wait on longer operations WILL result
        in a timeout error."""
        self.ask("*OPC?")

    def monitor(self):
        """This should be called immediately after any operation which will
        take a long time (>2 s) to complete.  It sets the OPC (operation complete)
        bit in the status register.  Subsequent calls to done() will check this
        bit and use it to determine if the long operation has completed yet."""
        self.write("*WAI;*OPC")

    def done(self):
        """This is a NON-BLOCKING query that returns True if the instrument has
        completed all previously assigned operations that were followed by a
        call to monitor(), and False if it is still busy. This clears the ESR
        register."""
        print("Requesting status byte.")
        n = int(self.readStatusByte())       #get status byte
        print("Status byte is " + str(n))
        opcbit = (n & 0x20) != 0     #check bit 5, event summary bit
        print("OPC bit is: ", opcbit)
        if opcbit == 1:                 #if operation is complete
            return True
        else:
            return False



class B2901A(Instrument):
    """This class represents and controls a Keysight B2901A SMU.  For operating
    details of this instrument, refer to Keysight document B2910-90030, titled
    "Keysight B2900 SCPI Command Reference"."""

    def __init__(self, device):
        self.description = "Keysight B2901 SMU"
        self.expectedMfr = "Keysight Technologies"
        self.expectedModel = "B2901A"
        self.VID = 0x0957
        self.PID = 0x8b18
        #call superclass constructor, which connects and gathers some info
        super().__init__(device, self.description)
        #instrument-specific additional setup
        self.write("*ESE 1")    #enable summary of bit 0, Event Status register, to enable *OPC monitoring
        self.write("*SRE 32")   #enable summary of bit 5, Status Byte, to enable *OPC monitoring


    #SOURCE control methods
    def setSourceFunctionToVoltage(self):
        self.write(":FUNC:MODE VOLT")

    def setSourceFunctionToCurrent(self):
        self.write(":FUNC:MODE CURR")

    def setVoltage(self,v):
        """Takes float argument."""
        self.write(":VOLT " + str(v))

    def setCurrent(self,a):
        """Takes float argument."""
        self.write(":CURR " + str(a))

    def setOutputShapeToDC(self):
        self.write(":FUNC DC")

    def setOutputShapeToPulse(self):
        self.write(":FUNC PULS")

    def setVoltageModeToList(self):
        self.write(":SOURCE:VOLT:MODE LIST")

    def setVoltageModeToFixed(self):
        self.write(":SOURCE:VOLT:MODE FIX")

    def setVoltageList(self, vsl):
        """vsl is list of voltages for sweep"""
        s = str(vsl).split(']')[0].split('[')[1]  #make string from list, remove brackets
        self.write(":LIST:VOLT " + s)

    def enableContinuousTrigger(self, en=True):
        if en:
            self.write(":FUNC:TRIG:CONT ON")
        else:
            self.write(":FUNC:TRIG:CONT OFF")

    def enableSourceVoltAutorange(self, en=True):
        if en:
            self.write(":SOUR:VOLT:RANG:AUTO ON")
        else:
            self.write(":SOUR:VOLT:RANG:AUTO OFF")

    #SENSE control methods
    #--------------------------
    def setSenseFunctionToCurrent(self):
        self.write(":SENS:FUNC CURR")

    def setSenseFunctionToVoltage(self):
        self.write(":SENS:FUNC VOLT")

    def setCurrentComplianceLevel(self,a):
        self.write(":SENS:CURR:PROT " + str(a))

    def setVoltageProtectionLevel(self,v):
        self.write(":SENS:VOLT:PROT " + str(v))

    def enableRemoteSensing(self, en=True):
        if en:
            self.write(":SENS:REM ON")
        else:
            self.write(":SENS:REM OFF")

    def enableSenseCurrentAutorange(self, en=True):
        if en:
            self.write(":SENS:CURR:RANG:AUTO ON")
        else:
            self.write(":SENS:CURR:RANG:AUTO OFF")

    #TRIGGER control
    #-------------------------
    def setTriggerAcquisitionDelay(self, delay):
        """set delay between trigger and acquisition"""
        self.write(":TRIG:ACQ:DEL " + str(delay))

    def setTriggerTransientDelay(self, delay):
        """set delay between trigger and transient (output change)"""
        self.write(":TRIG:TRAN:DEL " + str(delay))

    def setArmCount(self, count):
        self.write(":ARM:COUNT " + str(count))

    def setArmImmediate(self):
        self.write(":ARM:IMM")

    def setArmDelay(self, delay):
        self.write(":ARM:DELAY " + str(delay))

    def setTriggerSourceToTimer(self):
        self.write("TRIG:SOURCE TIMER")

    def setTriggerCount(self, count):
        self.write("TRIG:COUNT " + str(count))

    def setTriggerTimerInterval(self, interval):
        self.write("TRIG:TIMER " + str(interval))

    #Other
    #------------------------
    def enableOutput(self, en=True):
        if en:
            self.write(":OUTP ON")
        else:
            self.write(":OUTP OFF")

    def measure(self):
        """Perform a spot measurement using current parameters, returns a float."""
        return float(self.ask(":MEAS?"))

    def initiate(self):
        """Initiates a source/measure operation already set up"""
        self.write(":INIT")

    #Combination functions which make life easier
    #--------------------------
    def performVoltageListSweep(self, vlist, tstep, compliance=0.1):
        """Performs a list sweep, outputting voltage and measuring current.
        vlist is a list of voltages. tstep is the time step (seconds).
        compliance is current compliance limit (amps). Returns a list of two
        lists: [voltages, currents]."""
        points = len(vlist)
        self.setSourceFunctionToVoltage()        #output voltage
        self.enableSourceVoltAutorange(True)        #enable voltage autoranging
        self.setVoltageModeToList()                #using list sweep mode
        self.setVoltageList(vlist)                #load requested sweep list
        self.setSenseFunctionToCurrent()            #sensing current
        self.enableSenseCurrentAutorange(True)    #enable current autoranging
        self.setCurrentComplianceLevel(compliance)        #set current compliance
        self.setTriggerSourceToTimer()            #use timer as trigger source
        self.setTriggerTimerInterval(tstep)        #program the timer step
        self.setTriggerCount(points)            #number of data points to collect
        self.setTriggerAcquisitionDelay(tstep/10)
        self.enableOutput(True)                    #turn on output
        self.initiate()                            #begin measurement operation
        self.monitor()






class MSO2102A(Instrument):
    def __init__(self, device):
        self.description = "Rigol MSO2102A Oscilloscope"
        self.expectedMfr = "RIGOL TECHNOLOGIES"
        self.expectedModel = "MSO2102A"
        self.VID = 0x1ab1
        self.PID = 0x04b0
        #call superclass constructor, which connects and gathers some info
        super().__init__(device, self.description)
