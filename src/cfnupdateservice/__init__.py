#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-


import argparse
import json
import logging
import subprocess
import syslog
import unittest

from cfnupdateservice.logging import Logger, Levels
from datetime import datetime, timedelta
from hashlib import sha256
from time import sleep


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Waits for CloudFormation metadata updates and calls hooks on update.")

    parser.add_argument('--verbose', action="store_true", help="Emit verbose log statements.")
    parser.add_argument('-l', '--logging-method', type=str, choices=('stdout', 'stdout-json', 'syslog', 'syslog-json'),
        default="stdout", help="Configure the logging method.\nstdout and stdout-json log to standard output in " +
            "plaintext and JSON, respectively.\nsyslog and syslog-json log to syslog directly in plaintext and JSON, " +
            "respectively.")
    parser.add_argument('-s', '--stack-name', type=str, required=True,
        help="The CloudFormation logical stack name to check for updates.")
    parser.add_argument('-R', '--region', type=str, default='us-east-1',
        help="The AWS region that the CloudFormation stack is in.")
    parser.add_argument('-r', '--resource', type=str, required=True,
        help="The CloudFormation logical resource name to check for metadata updates.")
    parser.add_argument('-d', '--delay', type=int, default=1,
        help="The frequency, in minutes, of how often to check CloudFormation for updates.")

    # parse the arguments
    args = parser.parse_args()

    # construct the service
    service = CloudFormationUpdateService(
        stack_name=args.stack_name,
        resource=args.resource,
        region=args.region,
        delay_minutes=args.delay,
        logger=Logger(
            name="cfn-update-service",
            syslog=args.logging_method in ('syslog', 'syslog-json'),
            json=args.logging_method in ('stdout-json', 'syslog-json'),
            level=Levels.DEBUG if args.verbose else Levels.INFO
        )
    )

    # start the service
    try:
        service.start()
    except KeyboardInterrupt:
        # when a keyboard interrupt happens, just exit clean bro.
        pass


class CloudFormationUpdateService(object):
    """CloudFormation Update Service™"""

    def __init__(self, stack_name, resource, region, delay_minutes, logger):
        self.stack_name = stack_name
        self.resource = resource
        self.region = region
        self.delay_minutes = delay_minutes
        self.logger = logger
        # other
        self.last_tick = None
        self.last_checksum = None

    def start(self, condition = lambda: True):
        """Start the update service. This will block the main thread in a while/sleep loop."""
        self.last_tick = datetime.utcnow()

        while condition():
            if self.check_for_updates():
                self.execute_update()

            self.wait_until_next()

    def check_for_updates(self):
        """Perform update check."""
        if not self.last_checksum:
            # set it and return false
            self.last_checksum = self.fetch_metadata_checksum()
            return False

        # otherwise, last checksum is set so we can compare it against the current metadata
        previous_checksum = self.last_checksum
        current_checksum = self.fetch_metadata_checksum()

        # preserve it
        self.last_checksum = current_checksum

        # return true if there's an update, false otherwise
        return current_checksum != previous_checksum

    def wait_until_next(self):
        """Sleep until the next time to run."""
        difference = datetime.utcnow() - self.last_tick
        print difference
        # if there is a period to sleep for, then sleep
        if difference < timedelta(seconds=self.delay_minutes * 60):
            sleep(difference.total_seconds())

    def fetch_metadata_checksum(self):
        """Fetch metadata as a string from the CloudFormation stack resource."""
        p = subprocess.Popen(["/usr/bin/cfn-get-metadata", '-s', self.stack_name, '-r', self.resource, '--region',
                self.region], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            stdout, stderr = p.communicate()

            if p.returncode == 0:
                # success
                return sha256(stdout).hexdigest()
            else:
                self.logger.error("Unable to execute cfn-get-metadata ({returncode}): \n{output}".format(
                    returncode=p.returncode, output=stderr))

                return self.last_checksum or '1785cfc3bc6ac7738e8b38cdccd1af12563c2b9070e07af336a1bf8c0f772b6a' #nothing
        except KeyboardInterrupt as e:
            p.terminate()
            raise e

    def execute_update(self):
        """Execute an update by running cfn-init."""
        p = subprocess.Popen(['/usr/bin/cfn-init', '-v', '-s', self.stack_name, '-r', self.resource, '--region',
            self.region], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        try:
            stdout, stderr = p.communicate()

            if p.returncode == 0:
                # successful update, notify
                self.logger.info("Successfully updated based on the new CloudFormation metadata.")
            else:
                # failed update, notify
                self.logger.error("Unable to update based on the new CloudFormation metadata ({returncode}):\n{output}".format(
                    returncode=p.returncode, output=stdout))

        except KeyboardInterrupt as e:
            # terminate the process
            p.terminate()
            raise e


if __name__ == "__main__":
    main()
