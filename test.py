from instruments import B2901A
from os import listdir

"""Test script to verify that I have communication with SMU working"""
alldev = listdir("/dev/")

smu = B2901A(devicepath)

smu.reset()
