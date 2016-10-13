#!/usr/bin/python

import sys
from loglib import SNYLogger
import ftplib
import argparse
import re
import os
import calendar
import time 

def read_skipfile(infile, log):    
    skiplines = list()
    skipfile = open(infile, 'r')
    for line in skipfile:
        newline = line.rstrip('\r\n')
        linelength = len(newline)
        if linelength>0:
            log.logprint("Adding "+newline+" to skiplines")
            tmpobjects = re.compile(newline)        
            skiplines.append(tmpobjects)
    skipfile.close()
    return skiplines
    
    
    
#GET LOCAL FILELIST
def get_local_files(localpath,log):
    locallist = list()     
    os.chdir(localpath)
    log.logprint("*** GETTING LOCAL FILELIST ***")
    for name in os.listdir("."):
        if (not name.startswith('.')):
            statinfo = os.stat(name)
            
            if (statinfo.st_mode>=32768):
                entrytype = "file"
            else:
                entrytype = "dir"
            size = statinfo.st_size
            date = statinfo.st_mtime
            log.logprint("Date:"+str(int(date))+" type:"+entrytype+", name:"+name+" size:"+str(size))
            locallist.append({'name':name,'type':entrytype,'modify':int(date),'size':size})
    return locallist        


#
# login to ftp server
#    
def ftp_login(args, log):    
    ftp = ftplib.FTP()
    port = 21
    ftp.connect(args.host, port)
    try:
        log.logprint("Logging in...")
        ftp.login(args.user, args.password)
        log.logprint(ftp.getwelcome())
    except ftplib.error_perm, resp:
        log.logprint(str(resp))
    except:
        log.logprint("Login section failed..")
    return ftp
    
#
# get remote files 
#    
def get_remote_files(ftp, remotepath, args, log):
    # LIST CONTENTS
    contents = list()
    dirlist = list()
    log.logprint("*** GET REMOTE FILELIST ***")
    try:
        ftp.cwd(remotepath)
        # Entry point
        ftp.retrlines('MLSD', contents.append)
        for line in contents:    
#            log.logprint(line)
            entry = line.split(";")
            size = "0" #Set this because directories does not report size
            for item in entry:
                cell = item.split("=")
                if (cell[0]=="modify"):
                    date = cell[1]
                    modify=calendar.timegm(time.strptime(str(date), "%Y%m%d%H%M%S"))
                    #for loops/if checks are not blocks in python, i.e. no need to predefine modify 
                if (cell[0]=="type"):
                    entrytype=cell[1]
                if (cell[0]=="size"):
                    size = cell[1]
                if (len(cell[0])>0) and cell[0].startswith(' '):
                    #If string does not contain =, cell[1] will not be defined
                    #and first entry in cell[0] string will be whitespace
                    name = cell[0].lstrip()
            log.logprint("Date:"+str(modify)+" type:"+entrytype+" Name:"+name+" size:"+size)
            if (entrytype=='file' or entrytype=='dir'):   #Do not include current and parent dir entries
                dirlist.append({'name':name,'type':entrytype,'modify':int(modify),'size':size})
    except ftplib.error_perm, resp:
        log.logprint(str(resp))
        exit(1)
    return dirlist

def touch(fname):
    try:
        os.utime(fname, None)
    except:
        log.logprint("Updating mtime failed, "+fname+" does not exist")
        


def sync_files(ftp, args, skiplines, localpath, remotepath, log):

    locallist = get_local_files(localpath,log)

    remotelist = get_remote_files(ftp, remotepath, args, log)

    #Create dictionaries for easy lookup
    localdict = {}
    index = 0
    for lfile in locallist:
        localdict[lfile['name']]=index
        index+=1

    remotedict = {}
    index = 0
    for rfile in remotelist:
        remotedict[rfile['name']]=index
        index+=1

    # Traverse local filelist and
    # check if local file is present on remote 
    for lfile in locallist:
        #Check if file is present in skipfile
        #If present in skipfile, skip to next file in locallist   
        skiptonext = False
        for p in skiplines:
            m=p.match(lfile['name'])
            if (m):
                #log.logprint(lfile['name']+" match "+m.group()+", thus present in skipfile "+args.skipfile)
                log.logprint("Skipping: "+lfile['name'])
                skiptonext = True
                break
        if skiptonext: continue

        #
        #Check if remote has the local file
        #if present remote, type file and modify time is older than local file, set upload flag
        #
        upload = False   #Set to True here instead of False since this will handle the case where 
                        #remote does not exist, i.e. always upload except when remote is present 
                        #and up to date
        
        if lfile['name'] in remotedict:
            rfile = remotelist[remotedict[lfile['name']]] #Get fileinfo from remotelist using index 
            if lfile['type']=="file":
                log.logprint(lfile['name']+" is present remote : "+rfile['name'])
                if (lfile['modify']>rfile['modify']):
                    log.logprint("Local file is newer by "+str(lfile['modify']-rfile['modify'])+" seconds, try to upload...")
                    upload = True
            elif lfile['type']=="dir":
                log.logprint(lfile['name']+" is present remote and is directory: "+rfile['name'])
                sync_files(ftp, args, skiplines, lfile['name'], rfile['name'], log)
        elif lfile['type']=="dir":
            log.logprint(lfile['name']+" is NOT present remote and is directory: ")
            try:
                ftp.mkd(lfile['name'])
                log.logprint("CREATED DIR : "+lfile['name'])
                sync_files(ftp, args, skiplines, lfile['name'], lfile['name'], log)                
            except ftplib.all_errors, resp:
                log.logprint("ERROR: Failed to create directory "+lfile['name']+" - "+str(resp))            
        elif lfile['type']=="file":
            log.logprint(lfile['name']+" is NOT present remote and is file")
            upload = True
                
        #Handle upload flag            
        if (upload and lfile['type']=="file"):
            try:
                touch(lfile['name']) #Touch local file to set modify time to approx the same as the remote will get
                ftp.storbinary('STOR '+lfile['name'], open(lfile['name'], 'rb'))
                log.logprint("UPLOADED : "+lfile['name'])
            except ftplib.all_errors, resp:
                log.logprint("ERROR: Failed to upload "+lfile['name']+" - "+str(resp))

    #Make sure locally deleted items are deleted remotely
    for rfile in remotelist:
        if rfile['name'] not in localdict:
            if rfile['type']=="file":
                #Remote file is not present locally=>Delete it
                try:
                    ftp.delete(rfile['name'])             
                    log.logprint("DELETED: "+rfile['name'])
                except ftplib.all_errors, resp:
                    log.logprint("ERROR: Failed to delete "+rfile['name']+" - "+str(resp))
            elif rfile['type']=="dir":
                log.logprint("Remote dir "+rfile['name']+" not present locally, delete it recursively")
                #Remote dir is not present locally, decend and recursively delete everything
                #TODO: recursive_delete(ftp, rfile['name'])
                delete_recursive(ftp, args, rfile['name'], log)
    ftp.cwd("..")
    os.chdir("..")
    
    
def delete_recursive(ftp, args, remotepath, log):

    remotelist = get_remote_files(ftp, remotepath, args, log)

    #Make sure locally deleted items are deleted remotely
    for rfile in remotelist:
        if rfile['type']=="file":
            try:
                ftp.delete(rfile['name'])             
                log.logprint("DELETED: "+rfile['name'])
            except ftplib.all_errors, resp:
                log.logprint("ERROR: Failed to delete "+rfile['name']+" - "+str(resp))
        elif rfile['type']=="dir":
            log.logprint("Remote dir "+rfile['name']+" not present locally, delete it recursively")
            delete_recursive(ftp, args, rfile['name'], log)
    ftp.cwd("..")
    try:
        ftp.rmd(remotepath)
        log.logprint("DELETED DIR: "+remotepath)
    except ftplib.all_errors, resp:
        log.logprint("ERROR: Failed to delete directory "+remotepath+" - "+str(resp))
    
    

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--host", help="ftp hostname", required=True)
parser.add_argument("-u", "--user", help="username on ftp server", required=True)
parser.add_argument("-p", "--password", help="password", required=True)
parser.add_argument("-d", "--debug", help="print debug to terminal, default False", action="store_true")
parser.add_argument("-b", "--basedir", help="Toplevel directory on ftp server, default www")
parser.add_argument("-t", "--path", help="Local toplevel directory, default ., i.e. current dir")
parser.add_argument("-s", "--skipfile", help="Do not upload files in <skipfile>, default name upload.skip")
parser.set_defaults(debug=False)
parser.set_defaults(skipfile="upload.skip")
parser.set_defaults(basedir="www")
parser.set_defaults(path=".")

args = parser.parse_args()

log = SNYLogger(basename="upload", size_limit=10, no_logfiles=2, stdout=args.debug)

skiplines = read_skipfile(args.skipfile, log)

ftp = ftp_login(args, log)

sync_files(ftp, args, skiplines, args.path, args.basedir, log)
                        
ftp.quit()      



