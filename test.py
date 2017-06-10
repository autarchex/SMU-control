from instruments import B2901A

"""Test script to verify that I have communication with SMU working"""

smu = B2901A("/dev/usbtmc1")

smu.reset()
