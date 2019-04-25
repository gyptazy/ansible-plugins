#!/usr/bin/env python

# (C) 2019 Florian Paul Hoberg <florian.hoberg@credativ.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
 audit: Log Ansible meta information to CSV file.
 requirements:
   - configparser (pip)
   - datetime (pip)
   - cvs
 short_description: This callback mod. will log Ansible meta information to a CSV file.
 version_added: "2.0"
 description:
     - This callback module just logs any Ansible meta information
       to a given CSV file to make sure this can be audited. It
       makes sure that you can verify who ran which commands
       on defined limits with used extra-vars etc.
 options:
   logfile:
     description: Define path where to log (csv file).
     ini:
       - section: audit 
         key: logfile 
   enable:
     description: Enable logging (else it will run in dry-run mode).
     ini:
       - section: audit
         key: enable
'''

import os
import sys
import csv
import time
import configparser
from ansible.plugins.callback import CallbackBase

try:
   from __main__ import cli
except ImportError:
   cli = None

# Python 2.7 compatibilty
try:
   FileNotFoundError
except NameError:
   FileNotFoundError = IOError


class CallbackModule(CallbackBase):
   """
   This callback module will log Ansible
   meta information to a csv log file.
   """

   def __init__(self):
       super(CallbackModule, self).__init__()
       self.audit_config = '/etc/ansible/audit.ini'
       self.playbook_name = None
       self.run_id = None
       self.date = time.strftime("%d.%m.%Y")
       self.time = time.strftime("%H:%M:%S")
       self.limit = None
       self.tags = None
       self.extra_vars = None

       # Check if config file is present
       self.check_config_file(self.audit_config)

       # Obtain information from audit config file
       config = configparser.ConfigParser()
       config.read(self.audit_config)

       # Obtain logfile path
       self.audit_logfile = config['audit']['logfile']

       # Dryrun (will print to stdout instead of CSV file)
       self.audit_enable = config['audit'].getboolean('enable')

       # Obtain additional information of Ansible
       # options while running the playbook.
       if cli:
           if 'subset' in dir(cli.options): self.limit = cli.options.subset
           if 'tags' in dir(cli.options): self.tags = cli.options.tags
           if 'extra_vars' in dir(cli.options): self.extra_vars = cli.options.extra_vars


   def check_config_file(self, config_file):
       """
       Function to check if needed config file is present
       """
       try:
           config = open(config_file, 'r')
       except FileNotFoundError:
           print '\n[CRITICAL]: Could not load config file. Please check if /etc/ansible/audit.ini exists!'
           sys.exit(1)
       except PermissionError:
           print '\n[CRITICAL]: Could not load config file. Please check file permissions on /etc/ansible/audit.ini!'
           sys.exit(1)


   def v2_playbook_on_start(self, playbook):
       """
       Function to obtain information from Ansible
       while triggering the start of playbooks.
       """
       attrib = {}
       self.playbook_name = playbook._file_name
       self.run_id = playbook.get_plays()[0]._variable_manager._inventory.get_hosts()[0].get_vars().get('ansible_run_id')

       if self.limit is not None: attrib['Limit'] = self.limit
       if self.tags is not None: attrib['Tags'] = self.tags
       if self.extra_vars is not None: attrib['Extra Vars'] = ' '.join(self.extra_vars)

       # Make sure this will also work if users are
       # hidden due to security policies or no controlling
       # terminal is used.
       try:
           attrib['Executer'] = os.getlogin()
           self.executor = attrib['Executer']
       except:
           self.executor = "Unknown"


   def v2_runner_on_ok(self, result):
       """
       Function to obtain debug information
       from Ansible.
       """
       self._clean_results(result._result, result._task.action)
       self.debug = self._dump_results(result._result)


   def v2_playbook_on_task_start(self, task, is_conditional):
       """
       Function to obtain last executed task
       by Ansible.
       """
       self.task = task    # Get last executed task


   def v2_playbook_on_play_start(self, play):
       """
       Function to obtain last executed play
       by Ansible.
       """
       self.play = play    # Get last executed play


   def playbook_on_stats(self, stats):
       """
       Function to summerize all information
       """
       hosts = sorted(stats.processed.keys())
       self.hosts = hosts
       self.run_status = True

       # Iterate trough all hosts to check for
       # any failures
       for host in hosts:
           summary = stats.summarize(host)
           if summary['failures'] > 0:
               self.run_status = False

       self.host = host
       self.csv_write_content()


   def csv_write_header(self):
       """
       Fuction to write CSV header if empty
       without loading the whole file everytime.
       """
       # Create header elements
       header = ["Date", "Time", "Status", "Executor", "Playbook", "Limit", "Tags", "Extra-Vars", "Hosts"]
       try:
           with open(self.audit_logfile, 'a') as csv_file:
               csv_file_empty = os.stat(self.audit_logfile).st_size == 0
               writer = csv.writer(csv_file)
               if csv_file_empty:
                   writer.writerow(header)
           csv_file.close()
       # If file does not exists it will be
       # created during the run of this module
       except PermissionError:
           print '\n[CRITICAL]: Could not load log file. Please check file permissions!'
           sys.exit(1)


   def csv_write_content(self):
       """
       Function to write audit information to
       CSV file.
       """
       # Validate if header is present
       self.csv_write_header()

       # Validate ansible run status
       if self.run_status:
           ansible_status_run = "Ok"
       else:
           ansible_status_run = "Failed"

       # Create content elements
       row = [self.date, self.time, ansible_status_run, self.executor, self.playbook_name, self.limit, self.tags, self.extra_vars, self.host]

       try:
           with open(self.audit_logfile, 'a') as csv_file:
               # Write/append elements to CSV file
               writer = csv.writer(csv_file)
               writer.writerow(row)
           csv_file.close()
       except PermissionError:
           print '\n[CRITICAL]: Could not load CSV file. Please check file permissions!'
           sys.exit(1)
