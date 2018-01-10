
# developed by Gabi Zapodeanu, TSA, GPO, Cisco Systems

# !/usr/bin/env python3

import requests
import json
import time
import datetime
import urllib3
import logging
import sys
import select


# import provided modules

import utils
import spark_apis
import dnac_apis
import asav_apis
import init

from urllib3.exceptions import InsecureRequestWarning  # for insecure https warnings
from requests.auth import HTTPBasicAuth  # for Basic Auth

from PIL import Image, ImageDraw, ImageFont

from init import SPARK_AUTH, SPARK_URL, TROPO_KEY

from init import DNAC_URL, DNAC_USER, DNAC_PASS
DNAC_AUTH = HTTPBasicAuth(DNAC_USER, DNAC_PASS)

from init import ASAv_URL, ASAv_USER, ASAv_PASSW
ASAv_AUTH = HTTPBasicAuth(ASAv_USER, ASAv_PASSW)


urllib3.disable_warnings(InsecureRequestWarning)  # disable insecure https warnings


# The following declarations need to be updated based on your lab environment


ROOM_NAME = 'ERNA'

ASAv_URL = 'https://10.93.130.40'
ASAv_USER = 'python'
ASAv_PASSW = 'cisco'
ASAv_AUTH = HTTPBasicAuth(ASAv_USER, ASAv_PASSW)


UCSD_URL = 'https://10.94.132.69'
UCSD_USER = 'gzapodea'
UCSD_PASSW = 'cisco.123'
UCSD_KEY = '1D3FD49A0D474481AE7A4C6BD33EC82E'
UCSD_CONNECT_FLOW = 'Gabi_VM_Connect_VLAN_10'
UCSD_DISCONNECT_FLOW = 'Gabi_VM_Disconnect_VLAN_10'

ROOM_NAME = 'ERNA'
IT_ENG_EMAIL = 'gabriel.zapodeanu@gmail.com'


def main():
    """
    Vendor will join Spark Room with the name {ROOM_NAME}
    It will ask for access to an IP-enabled device - named {IPD}
    The code will map this IP-enabled device to the IP address {172.16.41.55}
    Access will be provisioned to allow connectivity from DMZ VDI to IPD
    """

    # save the initial stdout
    initial_sys = sys.stdout

    # the user will be asked if interested to run in demo mode
    # production (logging to files - erna_log.log, erna_err.log))

    # user_input = utils.get_input_timeout('If running in Demo Mode please enter y ', 10)

    user_input = 'y'
    if user_input != 'y':

        # open a log file 'erna.log'
        file_log = open('erna_log.log', 'w')

        # open an error log file 'erna_err.log'
        err_log = open('erna_err.log', 'w')

        # redirect the stdout to file_log and err_log
        sys.stdout = file_log
        sys.stderr = err_log

        # configure basic logging to send to stdout, level DEBUG, include timestamps
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format=('%(asctime)s - %(levelname)s - %(message)s'))

    # the local date and time when the code will start execution

    DATE_TIME = str(datetime.datetime.now().replace(microsecond=0))
    print('\nThe app started running at this time ' + DATE_TIME)

    user_input = 'y'
    user_input = utils.get_input_timeout('Enter y to skip next section : ', 10)

    if user_input != 'y':
        # verify if Spark Space exists, if not create Spark Space, and add membership (optional)

        spark_room_id = spark_apis.get_room_id(ROOM_NAME)
        if spark_room_id is None:
            spark_room_id = spark_apis.create_room(ROOM_NAME)
            print('- ', ROOM_NAME, ' -  Spark room created')

            # invite membership to the room
            spark_apis.add_room_membership(spark_room_id, IT_ENG_EMAIL)

            spark_apis.post_room_message(ROOM_NAME, 'To require access enter :  IPD')
            spark_apis.post_room_message(ROOM_NAME, 'Ready for input!')
            print('Instructions posted in the room')
        else:
            print('- ', ROOM_NAME, ' -  Existing Spark room found')

            spark_apis.post_room_message(ROOM_NAME, 'To require access enter :  IPD')
            spark_apis.post_room_message(ROOM_NAME, 'Ready for input!')
        print('- ', ROOM_NAME, ' -  Spark room id: ', spark_room_id)

        # check for messages to identify the last message posted and the user's email who posted the message
        # check for the length of time required for access

        last_message = (spark_apis.last_user_message(ROOM_NAME))[0]

        while last_message == 'Ready for input!':
            time.sleep(5)
            last_message = (spark_apis.last_user_message(ROOM_NAME))[0]
            if last_message == 'IPD':
                last_person_email = (spark_apis.last_user_message(ROOM_NAME))[1]
                spark_apis.post_room_message(ROOM_NAME, 'How long time do you need access for? (in minutes)  : ')
                time.sleep(10)
                if (spark_apis.last_user_message(ROOM_NAME))[0] == 'How long time do you need access for? (in minutes)  : ':
                    timer = 30 * 60
                else:
                    timer = int(spark_apis.last_user_message(ROOM_NAME)[0]) * 60
            elif last_message != 'Ready for input!':
                spark_apis.post_room_message(ROOM_NAME, 'I do not understand you')
                spark_apis.post_room_message(ROOM_NAME, 'To require access enter :  IPD')
                spark_apis.post_room_message(ROOM_NAME, 'Ready for input!')
                last_message = 'Ready for input!'

        print('\nThe user with this email: ', last_person_email, ' will be granted access to IPD for ', (timer/60), ' minutes')

    # get UCSD API key
    # ucsd_key = get_ucsd_api_key()

    # execute UCSD workflow to connect VDI to VLAN, power on VDI
    # execute_ucsd_workflow(ucsd_key, UCSD_CONNECT_FLOW)

    print('UCSD connect flow executed')

    # get the WJT Auth token to access DNA
    dnac_token = dnac_apis.get_dnac_jwt_token(DNAC_AUTH)
    print('\nThe DNA Center auth token is: ', dnac_token)

    # IPD IP address - DNS lookup if available

    ipd_ip = '10.93.140.35'

    # locate IPD in the environment using DNA C
    ipd_location_info = dnac_apis.locate_client_ip(ipd_ip, dnac_token)

    remote_device_hostname = ipd_location_info[0]
    vlan_number = ipd_location_info[2]
    interface_name = ipd_location_info[1]

    remote_device_location = dnac_apis.get_device_location(remote_device_hostname, dnac_token)

    print('\nThe IPD is connected to:')
    print('this interface:', interface_name, ', access VLAN:', vlan_number)
    print('on this device:', remote_device_hostname)
    print('located:       ', remote_device_location)

    # deployment of interface configuration files to the DC router

    dc_device_hostname = 'PDX-RO'
    project = 'ERNA'
    print('\nThe DC device name is: ', dc_device_hostname)

    dc_int_config_file = 'DC_Interface_Config.txt'
    dc_int_templ = dc_int_config_file.split('.')[0]

    cli_file = open(dc_int_config_file, 'r')
    cli_config = cli_file.read()

    dnac_apis.upload_template(dc_int_templ, project, cli_config, dnac_token)
    depl_id_dc_int = dnac_apis.deploy_template(dc_int_templ, project, dc_device_hostname, dnac_token)
    time.sleep(1)

    # deployment of routing configuration files to the DC router

    dc_rout_config_file = 'DC_Routing_Config.txt'
    dc_rout_templ = dc_rout_config_file.split('.')[0]

    cli_file = open(dc_rout_config_file, 'r')
    cli_config = cli_file.read()

    dnac_apis.upload_template(dc_rout_templ, project, cli_config, dnac_token)
    depl_id_dc_routing = dnac_apis.deploy_template(dc_rout_templ, project, dc_device_hostname, dnac_token)

    print('\nDeployment of the configurations to the DC Router started')

    time.sleep(1)

    # deployment of interface configuration files to the Remote router

    remote_int_config_file = 'Remote_Interface_Config.txt'
    remote_int_templ = remote_int_config_file.split('.')[0]

    cli_file = open(remote_int_config_file, 'r')
    cli_config = cli_file.read()

    dnac_apis.upload_template(remote_int_templ, project, cli_config, dnac_token)
    depl_id_remote_int = dnac_apis.deploy_template(remote_int_templ, project, remote_device_hostname, dnac_token)
    time.sleep(1)

    # deployment of routing configuration files to the Remote router

    remote_rout_config_file = 'Remote_Routing_Config.txt'
    remote_rout_templ = remote_rout_config_file.split('.')[0]

    cli_file = open(remote_rout_config_file, 'r')
    cli_config = cli_file.read()

    # update the template with the local info for the IPD
    # replace the $VlanId with the local VLAN access
    # replace the $IPD with the IPD ip address

    cli_config = cli_config.replace('$IPD', ipd_ip)
    cli_config = cli_config.replace('$VlanId', vlan_number)

    dnac_apis.upload_template(remote_rout_templ, project, cli_config, dnac_token)
    depl_id_remote_routing = dnac_apis.deploy_template(remote_rout_templ, project, remote_device_hostname, dnac_token)

    print('\nDeployment of the configurations to the Remote Router started')

    time.sleep(1)

    # check the deployment status after waiting for all jobs to complete - 5 seconds
    print('\nWait for DNA Center to complete template deployments')
    time.sleep(10)

    # dc_interface_status = dnac_apis.check_template_deployment_status(depl_id_dc_int, dnac_token)
    # dc_routing_status = dnac_apis.check_template_deployment_status(depl_id_dc_routing, dnac_token)
    # remote_interface_status = dnac_apis.check_template_deployment_status(depl_id_remote_int, dnac_token)
    # remote_routing_status = dnac_apis.check_template_deployment_status(depl_id_remote_routing, dnac_token)

    # print(dc_interface_status, dc_routing_status, remote_interface_status, remote_routing_status)
    # if dc_interface_status == 'SUCCESS' and dc_routing_status ==  'SUCCESS' and remote_interface_status == 'SUCCESS' and
        #remote_routing_status == 'SUCCESS':
        #print('\nAll templates deployment have been successful\n')

    # synchronization of devices configured - DC and Remote Router

    dc_sync_status = dnac_apis.sync_device(dc_device_hostname, dnac_token)[0]
    remote_sync_status = dnac_apis.sync_device(remote_device_hostname, dnac_token)[0]

    if dc_sync_status == 202:
        print('\nDNA Center started the DC Router resync')
    if remote_sync_status == 200:
        print('\nDNA Center started the Remote Router resync')
    print('\nWait for DNA Center to complete the resync of the two devices')
    time.sleep(240)

    path_visualisation_id = dnac_apis.create_path_visualisation('172.16.202.1', ipd_ip, dnac_token)

    print('\nWait for Path Visualization to complete')
    time.sleep(20)

    path_visualisation_info = dnac_apis.get_path_visualisation_info(path_visualisation_id, dnac_token)
    print('\nPath visualisation status: ', path_visualisation_info[0])
    print('\nPath visualisation details: ', path_visualisation_info[1])
    utils.pprint(path_visualisation_info)


    #create ASAv outside interface ACL to allow traffic
    ######################

    # Spark notification

    spark_apis.post_room_message(ROOM_NAME, 'Requested access to this device: IPD, located in our office ' +
                                 remote_device_location +' by user ' + last_person_email + ' has been granted for '
                                 + str(int(timer / 60)) + ' minutes')

    # Tropo notification - voice call

    # voice_notification_result = tropo_notification()
    # spark_apis.post_room_message(ROOM_NAME, 'Tropo Voice Notification: ' + voice_notification_result)

    # time.sleep(timer)
    input('Input any key to continue ! ')

    #
    #  restore configurations to initial state
    #

    #  restore DC router config

    dc_del_file = 'DC_Delete.txt'
    dc_del_templ = dc_del_file.split('.')[0]

    cli_file = open(dc_del_file, 'r')
    cli_config = cli_file.read()

    dnac_apis.upload_template(dc_del_templ, project, cli_config, dnac_token)
    depl_id_dc_del = dnac_apis.deploy_template(dc_del_templ, project, dc_device_hostname, dnac_token)

    print('\nDC Router restored to the baseline configuration')

    time.sleep(1)

    #  restore Remote router config

    remote_del_file = 'Remote_Delete.txt'
    remote_del_templ = remote_del_file.split('.')[0]

    cli_file = open(remote_del_file, 'r')
    cli_config = cli_file.read()

    # update the template with the local info for the IPD
    # replace the $VlanId with the local VLAN access
    # replace the $IPD with the IPD ip address

    cli_config = cli_config.replace('$IPD', ipd_ip)
    cli_config = cli_config.replace('$VlanId', vlan_number)

    dnac_apis.upload_template(remote_del_templ, project, cli_config, dnac_token)
    depl_id_remote_del = dnac_apis.deploy_template(remote_del_templ, project, remote_device_hostname, dnac_token)

    print('\nRemote Router restored to the baseline configuration')

    time.sleep(1)


    # execute UCSD workflow to discoconnect VDI to VLAN, power on VDI
    # execute_ucsd_workflow(ucsd_key, UCSD_DISCONNECT_FLOW)

    print('|nUCSD disconnect flow executed')

    # Spark notification

    spark_apis.post_room_message(ROOM_NAME, 'Access to this device: IPD has been terminated')

    # restore the stdout to initial value
    sys.stdout = initial_sys

    # the local date and time when the code will end execution

    DATE_TIME = str(datetime.datetime.now().replace(microsecond=0))
    print('\n\nEnd of application run at this time ', DATE_TIME)


if __name__ == '__main__':
    main()

