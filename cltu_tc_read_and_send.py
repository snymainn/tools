#!/usr/bin/env python

# Script that can read commands recorded from logging port of Safaran/Zodiac Cortex CRT
# and send them to the Cortex CRT SLE Gateway using this library: https://gitlab.com/librecube/lib/python-sle-user
# Filename recorded_tc_data used in code

import logging
import logging.handlers
level = logging.DEBUG
format = "%(asctime)s %(funcName)s - %(levelname)s : %(message)s" 
handlers = [logging.handlers.RotatingFileHandler('cltu.log', mode='w', maxBytes=5000000, backupCount=10), logging.StreamHandler()]
logging.basicConfig(level = level, format = format, datefmt='%Y-%m-%dT%I:%M:%S.%p', handlers = handlers)
import time
import sle
from cltu_tc_read_and_send_config import config

#Do manual rollover of the logfiles since I only want one testrun in each logfile
logging.handlers.RotatingFileHandler.doRollover(handlers[0])



cltu = sle.CltuUser(
    service_instance_identifier=config['CLTU']['CLTU_INST_ID'],
    responder_ip=config['CLTU']['SLE_PROVIDER_HOSTNAME'],
    responder_port=int(config['CLTU']['SLE_PROVIDER_TC_PORT']),
    auth_level='bind',
    local_identifier=config['CLTU']['INITIATOR_ID'],
    peer_identifier=config['CLTU']['RESPONDER_ID'],
    local_password=config['CLTU']['PASSWORD'],
    peer_password=config['CLTU']['PEER_PASSWORD'],
    heartbeat=30,
    deadfactor=5,
    buffer_size=32768,
    version_number=2)

def return_status_handler(data):
    cltu.production_status = str(data['cltuProductionStatus'])
    cltu.buffer_available = data['cltuBufferAvailable']
    print(data.prettyPrint())

def return_parameter_handler(data):
    print(data.prettyPrint())


cltu.status_report_handler = return_status_handler
cltu.parameter_handler = return_parameter_handler


cltu.bind()
time.sleep(2)

if cltu.state == 'ready':

    cltu.schedule_status_report()
    time.sleep(2)
    cltu.get_parameter('plopInEffect')
    time.sleep(2)
    cltu.start()
    time.sleep(2)

    try:
        while cltu.production_status != 'operational':
            logging.info("cltuProductionStatus : " + str(cltu.production_status))
            time.sleep(2)
            cltu.schedule_status_report()
        command_counter = 0
        with open("recorded_tc_data", "rb") as f:  
            header = f.read(36)
            while header:
                packet_len = int.from_bytes(header[4:8], "big")
                preamble = "".join(map(hex, header[:4]))
                cmd_type = int.from_bytes(header[24:28], "big")
                if (cmd_type != 1): #Filter out telecommands that are not of type 1
                    logging.debug("Preamble : " + preamble + " cmd_type: " + str(cmd_type) + " skipping ")
                    f.read(packet_len-36)
                else:
                    tc_length = int((int.from_bytes(header[32:36], "big"))/8)
                    tc = f.read(tc_length)        
                    logging.debug("Preamble : " + preamble + ", tc length : " + str(tc_length) + " cmd_type: " + str(cmd_type))
                    #DELAY 10 means 10 microseconds (gives -1 in protocol to Cortex), 1 means 1 microsecond which is not valid
                    logging.debug(str(cltu.buffer_available) + " " + str(tc_length*10) + " " + str(cltu.production_status))
                    command_sent = 0
                    while (not command_sent):
                        if (cltu.buffer_available > (tc_length*10) and cltu.production_status == 'operational'):
                            cltu.transfer_data(tc, delay=10, notify=True)
                            #cltu.transfer_data(tc, notify=True) #For no delay
                            command_counter += 1
                            command_sent = 1
                        else:
                            logging.info("buffer size<tc length * 10 or prod status is not operational, "
                                         "sleep 10 sec and check status")
                            cltu.schedule_status_report()
                            time.sleep(10)
                        logging.info("cltuProductionStatus : " + str(cltu.production_status))
                        logging.info("cltuBufferAvailable : " + str(cltu.buffer_available))
                        logging.info("Command counter : " + str(command_counter))
                    trailer = f.read(packet_len-tc_length-36)
                header = f.read(36)

    except KeyboardInterrupt:
        pass

    finally:
        input("Press key to unbind")
        cltu.stop()
        time.sleep(2)
        cltu.schedule_status_report()
        time.sleep(2)
        cltu.unbind(reason='other')  # avoid instance to be unloaded
        time.sleep(2)

else:
    print("Failed binding to Provider. Aborting...")
