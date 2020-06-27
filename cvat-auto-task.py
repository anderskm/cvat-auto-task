#!/usr/bin/env python3

import argparse
import copy
import datetime
import glob
import json
import logging
import os
import sys
import time
from cvatapi import CVATAPI

def main():
    # Setup input argument parser
    parser = argparse.ArgumentParser()

    parser_group_server = parser.add_argument_group('Server')
    parser_group_server.add_argument('--host', action='store', default='localhost', type=str, help='IP or URL of the server (default: %(default)s)')
    parser_group_server.add_argument('--port', action='store', default='8080', type=str, help='Port of the server (default: %(default)s)')
    parser_group_server.add_argument('--username', action='store', required=True, type=str, help='Username used for authentication at server.')
    parser_group_server.add_argument('--password', action='store', required=True, type=str, help='Password for associated username.')
    parser_group_server.add_argument('--https', action='store_true', help='Set flag to use https connection instead of http.')

    parser_group_local = parser.add_argument_group('Local')
    parser_group_local.add_argument('--local_share', action='store', default='', type=str, help='Path to folder containing subfolders with images. Folder must be shared with and mounted on server. (default: %(default)s)')

    parser_group_task = parser.add_argument_group('Task')
    parser_group_task.add_argument('--labels', action='store', default='labels.json', type=str, metavar='labels.json', help='Json-file specifying labels. (default: %(default)s)')
    parser_group_task.add_argument('--job_size', action='store', default=0, type=int, help='Number of images in each job in the task. If set to 0, all images are put into a single job. (default: %(default)s, type: %(type)s)')
    parser_group_task.add_argument('--overlap', action='store', default=0, type=int, help='Number of images to overlap between jobs. If set to 0, no image overlap between jobs. (default: %(default)s, type: %(type)s)')
    parser_group_task.add_argument('--image_quality', action='store', default=80, type=int, help='Image quality (0-100) of jpeg images. (default: %(default)s, type: %(type)s)')

    parser_group_debug = parser.add_argument_group('Debug')
    parser_group_debug.add_argument('--debug', action='store_true', help='Set flag to print additional debug info.')

    # Parse input arguments
    args = parser.parse_args()

    # Setup log
    if (args.debug):
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(filename='vjd_task_creation.log', format='%(asctime)s[%(levelname)s] %(message)s', datefmt='[%Y.%m.%d %H:%M:%S]', level=log_level)
    console = logging.StreamHandler()
    console.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s[%(levelname)s] %(message)s', datefmt='[%Y.%m.%d %H:%M:%S]')
    # tell the handler to use this format
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

    args2 = copy.deepcopy(args)
    setattr(args2, 'password', '***') # Hide password before adding arguments to the log
    logging.debug('Program arguments: ' + args2.__str__())

    # Quick and dirty: Encapsule everything in a try-catch to catch any errors and add them to the log
    try:
        # Read labels
        f = open(args.labels)
        labels = json.load(f)
        f.close()

        logging.info('Scanning for folders...')
        logging.info('Main folder: ' + args.local_share)
        folders = [f for f in os.listdir(args.local_share) if os.path.isdir(os.path.join(args.local_share, f))]
        logging.info('Found ' + str(len(folders)) + ' folders: ' + ':'.join(folders))

        logging.info('Connecting to server (' + args.host +':' +  args.port + ')...')
        cvat = CVATAPI(server_host=args.host, server_port=args.port, username=args.username, password=args.password, use_https=args.https)

        logging.info('Retrieving tasks...')
        tasks = cvat.get_tasks()
        logging.info('Found ' + str(len(tasks)) + ' task(s) on the server:')
        for task in tasks:
            logging.info(task)

        task_names = [task.name for task in tasks]

        folders_no_match = list(set(folders) - set(task_names))
        logging.info('Folders (' + str(len(folders_no_match)) + ') not matching any tasks:')
        logging.info(':'.join(folders_no_match))

        if (len(folders_no_match) == 0):
            logging.info('All folders accounted for. No new tasks created.')
        if (len(folders_no_match) > 0):
            logging.info('Creating new tasks for folders with no match...')

            for folder in folders_no_match:
                logging.info('Processing folder: ' + folder)
                image_files = glob.glob(os.path.join(args.local_share, folder,'*.jpg'))
                image_files = [os.path.join(folder, os.path.split(i)[1]).replace('\\','/') for i in image_files]
                logging.info('Found ' + str(len(image_files)) + ' images')
                logging.debug(';'.join(image_files))
                
                logging.info('Creating task')
                task = cvat.create_task(name=folder, labels=labels, segment_size=args.job_size, overlap=args.overlap)

                logging.info('Adding images to task...')
                task.add_data(share_files=image_files, image_quality=args.image_quality)

                # Wait for server to finish adding data to task. Check status every 1 second
                time.sleep(1.0)
                status = task.status()
                while status['state'] in ['Queued','Started']:
                    logging.debug('State: ' + status['state'] + ' Message: ' + status['message'])
                    time.sleep(1.0)
                    status = task.status()
                if status['state'] == 'Failed':
                    logging.warning('\033[1;33mState: ' + status['state'] + ' Message: ' + status['message']+'\033[0m')
                else:
                    logging.info('State: ' + status['state'] + ' Message: ' + status['message'])

        logging.info('Done')

    except Exception as e:
        logging.error('\033[1;91mError occured\033[0m')
        logging.error('\033[1;91m' + str(e) + '\033[0m')
        raise e


if __name__ == '__main__':
    main()