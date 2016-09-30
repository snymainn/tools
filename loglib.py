#
# USE: 
# <object> = SNYLogger(logpath=[path],basename=<basename>,no_logfiles=<max logfiles>, 
#                  stdout=<print to stdout>, size_limit=<filesize in MB>)
# no_logfiles : default 10
# stdout      : default 0, for debugging
# size_limit  : default 0, If optional parameter size_limit is given it will not open new file unless 
#               the filesize of the last logfile has reached given size. This is useful when you are 
#               running a script very often from a crontab and does not want to open a new logfile all the time.
#
# Import:
# from loglib import SNYLogger
#
# Ex - run many times:
# log = SNYLogger(basename="my_program")
# log.logprint("Write a logtext")
#
# Ex - running continously: 
# log = SNYLogger(basename="my_program", size_limit=10)
# log.logprint("Write logtext")


from dircache import listdir
from time import gmtime,strftime
import os
import sys
import time

class SNYLogger:
    def __init__(self, logpath=".",basename = "set_sensible_basename", no_logfiles = 10, stdout = 0, size_limit = 0):
        self.logpath = logpath
        self.basename = basename
        self.no_logfiles = no_logfiles
        self.stdout = stdout
        self.size_limit = size_limit
        self.filehandle = 0
        self.pathname = ''

        self.rotate_files()


    def logprint(self, text):
        nowstring = strftime("%Y-%m-%dT%H:%M:%S", gmtime())
        if (self.filehandle) :
            if (self.size_limit):
                filesize=os.fstat(self.filehandle.fileno()).st_size
                if ((self.size_limit * 1024 * 1024) < filesize):
                #if ((self.size_limit) * 50 < filesize):
                    logstring = "%s : Filesize %d reached on %s, rotating file inside logprint\n" % (nowstring, filesize,self.pathname)
                    print logstring
                    self.filehandle.write(logstring)
                    self.filehandle.flush()
                    os.fsync(self.filehandle.fileno())
                    self.filehandle.close()
                    self.rotate_files()
            
            self.filehandle.write(nowstring+' : '+text+'\n')
            self.filehandle.flush()
            if (self.stdout):
                print "%s : %s" % (nowstring,text)
                sys.stdout.flush()


    def rotate_files(self):
        logfilename = self.basename+'.log'
        #print "logfilename : %s" % logfilename
        dirlist = []
        dirlist = listdir(self.logpath)
        largest = 0
        num_files = 0
        logfiles = []
        new = 0
        #FIND ONLY MATCHING FILES and FIND LARGEST #
        for filename in dirlist:
            pos = filename.find(logfilename)
            if (pos>=0) : 
                num_files = num_files + 1;
                nummer = int(filename.split('.')[-1])
                if (nummer > largest) :
                    largest = nummer
                logfiles.append(filename)
                #print "YES : %s, %s, %d, %d" % (filename, pos, nummer, num_files)
            #else :
                #print "NO: %s, %s" % (filename, pos)

        #CLEANUP OLD FILES
        if (num_files > self.no_logfiles):
            for filename in logfiles:
                nummer = int(filename.split('.')[-1])
                if (nummer < (largest-self.no_logfiles+1)):
                    pathname = "%s/%s" % (self.logpath,filename)
                    try:
                        os.remove(pathname)
                    except OSError, e:
                        stderr.write("Failed to delete "+pathname+', '+e)
                    #else:
                        #print "DELETED : %s " % pathname

        #GET FILESIZE OF LAST FILE
        pathname = "%s/%s.%d" % (self.logpath,logfilename,largest)
        filesize = 0
        if ( os.path.exists(pathname)) :
            filesize = os.stat(pathname).st_size
        
        #IF SIZE LIMIT DEFINED AND CURRENT FILESIZE IS REACHED, CREATE NEW #
        if (self.size_limit):
            if ((self.size_limit * 1024 * 1024) < filesize) :
            #if ((self.size_limit*50) < filesize) :
                largest = largest + 1
                new = 1
        else:
            #IF SIZE LIMIT NOT DEFINED, CREATE NEW #
            largest = largest + 1
            new = 1

        pathname = "%s/%s.%d" % (self.logpath,logfilename,largest)

        try:
            filehandle = open(pathname, 'a',0)
        except IOError,e:
            stderr.write("Failed to open "+pathname+', '+e)
        else:
            nowstring = strftime("%Y-%m-%dT%H:%M:%S", gmtime())
            if (new) :
                filehandle.write(nowstring+' : '+"Opened new logfile - "+pathname+'\n')
            else:
                filehandle.write(nowstring+' : '+"Appending logfile - "+pathname+'\n')
            self.filehandle = filehandle
            self.pathname = pathname







