import os

"""This module contains control classes for USB Test & Measurement Class
(USBTMC) instruments and a simplistic interface to the kernal USBTMC driver."""

class usbtmc:
    """Simplistic USB-TMC (Test & Measurement Class) 'driver'.
    Really, the kernel driver does all the real work.  The device needs to
    have already enumerated as a USB-TMC device to the system, i.e., there is
    a "/dev/usbtmc0" or similar entry present in /dev directory."""

    def __init__(self, device):
        """Argument 'device' (string) is path to a virtual file in /dev, typically /dev/usbtmc0 or /dev/usbtmc1"""
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

    def ask(self, command, length = 4000):
        """combined write-read for commands that end in '?', for convenience."""
        self.write(command)
        return self.read(length)

    def identify(self):
        return self.ask("*IDN?", 300)

    def reset(self):
        self.write("*RST")


class Instrument:
    """Template class for generic instruments.  Other specific instruments in this module inherit from this."""
    def __init__(self, device):
        print("Connecting to a Keysight B2901A SMU at ", device)
        self.port = usbtmc(device)
        print("Requesting device to identify...")
        self.name = self.port.identify()
        print("Device replied: \"" + self.name + "\"")

    def close(self):
        print("Disconnecting from instrument.")
        self.port.close()

    def write(self, command):
        """Write a command string to the instrument."""
        self.port.write(command)

    def read(self, length):
        """Read data from the instrument."""
        return self.port.read(length)

    def reset(self):
        """Reset the instrument."""
        self.port.reset()



class B2901A(Instrument):
    def __init__(self, device):
        super().__init__(device)	#call superclass constructor which gets us connected
        self.description = "B2901 SMU"

    def setFixedDCVmode(self):
        """Set to DC output mode."""
        self.port.write(":FUNC DC")
        self.port.write(":SOUR:FUNC:MODE:VOLT")
        self.port.write(":SOUR:VOLT:MODE:FIX")

    def setSourceVoltAutorange(on):
        """If on==True, turns on autorange for voltage output, else turns off"""
        if(on):
           onval = 1
        else:
           onval = 0 
        self.port.write(":SOUR:VOLT:RANG:AUTO " + onval)
     
