import os

"""This module contains control classes for USB Test & Measurement Class
(USBTMC) instruments and a simplistic interface to the kernal USBTMC driver."""

class usbtmc:
    """Simplistic USB-TMC (Test & Measurement Class) 'driver'.
    Really, the kernel driver does all the real work.  The device needs to
    have already enumerated as a USB-TMC device to the system, i.e., there is
    a "/dev/usbtmc0" or similar entry present in /dev directory."""

    def __init__(self, device):
        """Argument 'device' (string) is path to an entry in /dev, typically /dev/usbtmc0 or /dev/usbtmc1"""
        self.device = device
        self.dfile = os.open(device, os.O_RDWR)

    def close(self):
        """closes the underlying file.  Not actually expected to be necessary."""
        os.close(dfile)
        self.dfile = ""

    def read(self, length = 4000):
        """Reads (text) from instrument.  Reads byte vector (file is binary),
        decodes into a string, strips leading/trailing whitespace and terminal newline"""
        return os.read(self.dfile, length).decode().strip()

    def readb(self, length = 4000):
        """reads without any conversion, so returns a byte vector."""
        return os.read(self.dfile, length)

    def write(self, command):
        """Writes (text) to instrument. Adds a terminal newline and decodes to bytes,
        because file is open as binary, then sends it"""
        cmd = command + "\n"
        os.write(self.dfile, cmd.encode());

    def writeb(self, command):
        """writes without any conversion, so sends a byte vector.  Will fail if given a string."""
        os.write(self.dfile, command)


class Instrument:
    """Template class for generic instruments.  Other specific instruments in this module inherit from this."""
    def __init__(self, device, description="USB TMC instrument"):
        print("Connecting to " + description + " at " + device)
        self.port = usbtmc(device)
        print("Requesting device to identify...")
        self.idn = self.identify()
        print("Device replied: \"" + self.idn + "\"")
        #extract manufacturer, model number, serial number, and revision number
        self.mfr, self.model, self.sn, self.version = self.idn.split(",")
        if self.expectedModel not in self.model:
            print("Warning: device returned model \'" + self.model + "\', expected \'" + self.expectedModel + "\'")

    def close(self):
        print("Disconnecting from instrument.")
        self.port.close()

    def write(self, command):
        """Write a command string to the instrument."""
        self.port.write(command)

    def read(self, length):
        """Read data from the instrument."""
        return self.port.read(length)

    def ask(self, command, length = 4000):
        """combined write-read for commands that end in '?', for convenience."""
        self.write(command)
        return self.read(length)

    def identify(self):
        return self.ask("*IDN?", 300)

    def reset(self):
        self.write("*RST")


class B2901A(Instrument):
    """This class represents and controls a Keysight B2901A SMU.  For operating
    details of this instrument, refer to Keysight document B2910-90030, titled
    "Keysight B2900 SCPI Command Reference"."""

    def __init__(self, device):
        self.description = "Keysight B2901 SMU"
        self.expectedMfr = "Keysight Technologies"
        self.expectedModel = "B2901A"
        #call superclass constructor, which connects and gathers some info
        super().__init__(device, self.description)

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

    def setVoltageList(self,vsl):
        """vsl is list of voltages for sweep"""
        s = ""
        for v in vsl:
            s.append(str(v) + ",")  #create comma separated value string
        s = s[:-1]      #remove final command
        self.write(":LIST:VOLT " + s)

    def setCurrentComplianceLevel(self,a):
        self.write(":SENS:CURR:PROT " + str(a))

    def setVoltageProtectionLevel(self,v):
        self.write(":SENS:VOLT:PROT " + str(v))

    def enableOutput(self,en=True):
        if en:
            self.write(":OUTP ON")
        else:
            self.write(":OUTP OFF")

    def enableRemoteSensing(self,en=True):
        if en:
            self.write(":SENS:REM ON")
        else:
            self.write(":SENS:REM OFF")

    def enableContinuousTrigger(self,en=True):
        if en:
            self.write(":FUNC:TRIG:CONT ON")
        else:
            self.write(":FUNC:TRIG:CONT OFF")

    def enableSourceVoltAutorange(self,en=True):
        if en:
            self.write(":SOUR:VOLT:RANG:AUTO ON")
        else:
            self.write(":SOUR:VOLT:RANG:AUTO OFF")

    def measure(self):
        """Perform a spot measurement using current parameters, returns a float."""
        return float(self.ask(":MEAS?"))

    def initiate(self):
        """Initiates a source/measure operation already set up"""
        self.write(":INIT")

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



class MSO2102A(Instrument):
    def __init__(self, device):
        self.description = "Rigol MSO2102A Oscilloscope"
        self.expectedMfr = "RIGOL TECHNOLOGIES"
        self.expectedModel = "MSO2102A"
        #call superclass constructor, which connects and gathers some info
        super().__init__(device, self.description)
