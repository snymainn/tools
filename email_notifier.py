#!/usr/local/bin/python3
#
# Easy utilty to check pop3 email and dump it into an mbox file
# Example:
#  /<path>/email_notifier.py -s <server> -u <user> -p <password>
#
# Tip to configure alpine:
# In case of SMTP timeouts: Find "Customized headers" and set it to "From: <your@email>
# Avoid writing master password to decrypt smtp password:
#  cd ~/.alpine-smime/.pwd
#  mv MasterPassword.key MasterPassword.key.orig
#  openssl rsa -in MasterPassword.key.orig -out MasterPassword.key
#List of SMTP servers for sending mail. If blank: Unix Alpine uses sendmail.
#  smtp-server=<pop3 server>:587/tls/user=<pop3 username>/novalidate-cert/debug


import ntfy
import poplib
import time
import os.path
import os
import argparse
from email.header import decode_header
import sys
#Local library paths, please change
libpath = os.environ['HOME']+"/gitwork/tools/"
sys.path.append(libpath)

#THIS MIGHT BE NECESSARY TO CHANGE 
ntfy_exe = "/usr/local/bin/ntfy"

from loglib import SNYLogger



#TODO: Add email purge time

#Main check function
def checkMailAccount(server,user,password,email_path,index):
    #Only SSL and port 995 supported, DO NOT USE non-encryptet login
    try:
        pop3 = poplib.POP3_SSL(server, 995)
        pop3.user(user)
        auth = pop3.pass_(password)
    except Exception as error:
        log.logprint("[!] chekcing {0} failed, reason:{1}" % format(user, str(error)))
        exit(1)

    #If login succeded, continue
    if "+OK" in auth.decode():
        messages,numbytes=pop3.stat() #Get number of messages on server
        #If more than zero messages, do something
        if (messages > 0):   
            message_response, message_list, message_octets = pop3.uidl() # Get unique id's
            download = []
            # Spin through all downloaded unique id's and check if they are already read or new
            for item in message_list:
                message_no, uid=item.decode().split()
                # Find new messages (i.e not present in index read from indexfile)
                if uid not in index:
                    log.logprint("New message: %s, UID %s" % (message_no, uid))
                    download.append(int(message_no))
            if (os.path.isdir(email_path)):
                try:
                    mbox_out = open(email_inbox,"a") # Open mbox file for appending new messages
                except IOError as e:
                    log.logprint(str(e))
                    exit(1)
                subject_text = ""
                from_text = "From: "
                count = 0 # Counter for deciding when to insert comma in notification text
                # Spin through all messages that should be downloaded and get them
                for body_no in download:
                    count+=1
                    log.logprint("Processing message : %d" % body_no)
                    body_response, body, body_octet = pop3.retr(body_no) # Retrieve message from server
                    localtime = time.asctime(time.localtime(time.time())) # Make time to print in mbox header
                    decoded_line = ""
                    mbox_out.write("From email_notifier "+localtime+'\n') # Write mbox header
                    # Spin through all lines in body, decode from byte text and write to mbox
                    for line in body:
                        try:
                            decoded_line = line.decode()
                        except:
                            log.logprint("WARNING: Cannot decode string %s as unicode" % line)
                            try:
                                decoded_line = line.decode('ISO-8859-1')
                            except:
                                log.logprint("ERROR: Cannot decode string %s" % line)
                                continue
                        mbox_out.write(decoded_line+'\n')
                        if (decoded_line.startswith("Subject: ")):
                            subject_text = subject_text+", "+get_header_info(decoded_line)
                        if (decoded_line.startswith("From: ") and count > 1):
                            from_text = from_text+", "+get_header_info(decoded_line)
                        elif (decoded_line.startswith("From: ")):
                            from_text = get_header_info(decoded_line)
                    mbox_out.write('\n') # Make sure there are blank lines between messages as required
                    mbox_out.write('\n') # in mbox standard specification
                mbox_out.close() # Close mbox file
                if (len(download)>0):
                    log.logprint("Notification: %s\n%s" % (from_text, subject_text))
                    notification_title = "%d new messages" % len(download)
                    if (len(from_text)>110):
                        from_text = from_text[0:109]
                    notification(notification_title, from_text)
                    update_email_index(email_path, message_list)
            else:
                log.logprint("ERROR: Failed to open %s" % email_inbox)
        return True
    else:
        return False

#
# Decode MIME header for output to notification panel
#
def get_header_info(decoded_line):
    title, text = decoded_line.split(' ', 1)
    decoded_text = decode_header(text)[0]
    text = decoded_text[0]
    text_coding = decoded_text[1]
    if (text_coding is not None):
        text = text.decode(text_coding)
    return text   
#
# Send notification
#
def notification(from_info, message):
    cmd = '"{0}" -t "{1}" send "{2}"'.format(ntfy_exe,from_info, message)
    log.logprint("ntfy command : "+cmd)
    os.system(cmd)

#
# Read indexfile of already read email
#
def read_email_index(path):
    file = path+"/"+email_index_file
    index = []
    if (os.path.isfile(file)):
        email_index = open(file, "r")
        index = email_index.read().splitlines()
        email_index.close()
    return index

#
# Update indexfile of messages present on pop3 server that is read and added to local mailbox
#
def update_email_index(path, index):
    file = path+"/"+email_index_file
    if (os.path.isdir(path)):
        email_index = open(file, "w")
        for item in index:
            uid=item.decode().split()[1]
            email_index.write(uid+'\n')
    else:
        log.logprint("ERROR: %s is not a directory" % path)
        exit(1)
    

######################
# Start main program 
######################

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--server", help="pop3 server address", required=True)
parser.add_argument("-u", "--user", help="username on pop3", required=True)
parser.add_argument("-p", "--password", help="password", required=True)
parser.add_argument("-d", "--debug", help="print debug to terminal, default 0", action="count")
parser.add_argument("-m", "--email_path", help="Path to mbox files, default [HOME]/mail/")
parser.add_argument("-i", "--email_inbox", help="Mbox files used by email program as INBOX, default .[USER]")
parser.set_defaults(debug=0)
parser.set_defaults(email_path=os.environ['HOME']+"/mail")
parser.set_defaults(email_inbox="."+os.environ['USER'])

args = parser.parse_args()

#Start logger
log = SNYLogger(basename=".email_notifier", logpath=args.email_path, size_limit=10, stdout=args.debug)

#Local paths, TODO to get from parameters
email_index_file = ".email_notifier_index"
email_inbox = args.email_path+"/"+args.email_inbox

log.logprint("Email path: %s" % args.email_path)
log.logprint("Email inbox : %s" % args.email_inbox)

index = read_email_index(args.email_path)

checkMailAccount(args.server, args.user, args.password, args.email_path, index)


