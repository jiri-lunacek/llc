llc
===

Leica Log Convert is a script (maybe a set of scripts in future) to convert Leica Application Log format into other data formats suitable for various geodetic software

Current status:

Single python script which reads Leica Log format version 8.02.
The only supported output format is currently GNet VRV format.


Usage:
python llc.py < data/testApp.log > output.vrv
