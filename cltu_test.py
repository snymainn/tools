#!/usr/bin/env python3
import argparse

from loglib import SNYLogger

######################
# Start main program 
######################

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", help="cortex binary datafile", required=True)
parser.add_argument("-d", "--debug", help="print debug to terminal, default 0", action="count")
parser.set_defaults(debug=0)

args = parser.parse_args()

#Start logger
log = SNYLogger(size_limit=10, stdout=args.debug)

log.logprint("File: %s" % args.file)

if (os.path.isfile(file)):
    with open(file) as f:
        while True:
            #Read cortex header
            header = f.read(64)
            if header != "":
                #Process header
            else
                break
            #Read the actual cortex data
            data = f.read(datalength)
            if data != "": 
                #Send data to cortex with sle
            else:
                break
            #Read trailer
            if f.read(4) == "":
                break
                
            

