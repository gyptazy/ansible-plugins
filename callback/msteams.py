#!/usr/bin/env python

# (C) 2019 Florian Paul Hoberg <florian.hoberg@credativ.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
 msteams: Send Ansible meta information to Microsoft Teams channel.
 requirements:
   - pymsteams (pip)
   - configparser (pip)
   - datetime (pip) 
 short_description: This callback mod. will send Ansible output to MS Teams.
 version_added: "2.7"
 description:
     - This callback module just sends start and finished messages
       to Microsoft Teams channels with additional Ansible meta
       information like limits, executed user, extra-vars etc.
 options:
   channel:
     description: Define URL to desired Microsoft Teams channel.
     ini:
       - section: teams
         key: channel
   enable_notify:
     description: Define if notifications should be sent (dry-run).
     ini:
       - section: teams
         key: enable_notify
   enable_start_notify:
     description: Define if a start notify should be sent.
     ini:
       - section: teams
         key: enable_start_notify
author:
    - Florian Paul Hoberg (@florianpaulhoberg) <florian.hoberg@credativ.de>
'''

import os
import sys
import datetime
import pymsteams
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
   This callback module will send Ansible meta
   information to Microsoft Teams chat channels.
   """

   def __init__(self):
       super(CallbackModule, self).__init__()
       self.msteams_config = '/etc/ansible/msteams.ini'
       self.playbook_name = None
       self.run_id = None
       self.start_time = datetime.datetime.now()
       self.limit = None
       self.tags = None
       self.extra_vars = None

       # Check if config file is present
       self.check_config_file(self.msteams_config)

       # Obtain information for Microsoft Teams
       # room API connection from config file.
       config = configparser.ConfigParser()
       config.read(self.msteams_config)

       # Channel URL
       self.ms_teams_room = config['teams']['channel']

       # Notify on start of playbook
       self.ms_teams_start_notify = config['teams'].getboolean('enable_start_notify')

       # Dryrun (will print to stdout instead of channel) 
       self.ms_teams_notify = config['teams'].getboolean('enable_notify')

       # Obtain additional information of Ansible
       # options while running playbooks.
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
           print '\n[CRITICAL]: Could not load config file. Please check if /etc/ansible/msteams.ini exists!'
           sys.exit(1)
       except PermissionError:
           print '\n[CRITICAL]: Could not load config file. Please check file permissions on /etc/ansible/msteams.ini!'
           sys.exit(1)


   def v2_playbook_on_start(self, playbook):
       """
       Function to obtain information from Ansible
       while triggering the start of playbooks.
       """
       information = {}
       attrib = {}
       self.playbook_name = playbook._file_name
       self.run_id = playbook.get_plays()[0]._variable_manager._inventory.get_hosts()[0].get_vars().get('ansible_run_id')

       if self.limit is not None: attrib['Limit'] = self.limit
       if self.tags is not None: attrib['Tags'] = self.tags
       if self.extra_vars is not None: attrib['Extra Vars'] = ' '.join(self.extra_vars)

       # Make sure this will also work if users are
       # hidden due to security policies or no controlling
       # terminal is used (e.g. Jenkins, Rundeck,...).
       try:
           attrib['Executer'] = os.getlogin()
           self.executor = attrib['Executer']
       except:
           self.executor = "Unknown"

       # Check if a start notify message of Playbook run should
       # be sent
       if self.ms_teams_start_notify:
           self.teams_send_msg_start()


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
       failures = False
       unreachable = False
       summary = {}
       self.end_time = datetime.datetime.now()
       self.duration_time = self.end_time - self.start_time

       # Iterate trough all hosts to check for
       # any failures
       for host in hosts:
           summary = stats.summarize(host)
           if summary['failures'] > 0:
               failures = True
           if summary['unreachable'] > 0:
               unreachable = True

       # Check if Playbook failed and notify to Microsoft Teams
       # chat channel
       if failures:
           self.host = host
           self.teams_send_msg_err()
       else:
           self.host = host
           self.summary = summary
       self.teams_send_msg_fin()


   def teams_send_msg_err(self):
       """
       Fuction to send error messages to defined Microsoft
       Teams chat channel with additional debug information.
       """
       try:
           # Create Microsoft Teams connection object
           ms_teams_connector = pymsteams.connectorcard(self.ms_teams_room)

           # Create Microsoft Teams message content
           ms_teams_connector.color('red')
           ms_teams_connector.title('Error: ' + str(self.host))
           ms_teams_connector.text('Could not execute ' + str(self.playbook_name) + ' on: ' + str(self.host) + ' on ' + str(self.task) + str(self.debug))

           # Send message to Microsoft Teams chat channel
           # (honor dry-run mode)
           if self.ms_teams_notify:
               ms_teams_connector.send()
           else:
               ms_teams_connector.printme()
       except:
           print '\n[CRITICAL]: Could not connect to Microsoft Teams.'


   def teams_send_msg_start(self):
       """
       Fuction to send start tasks messages to defined
       Microsoft Teams chat channel with additional run information.
       """
       try:
           # Create Microsoft Teams connection object
           ms_teams_connector = pymsteams.connectorcard(self.ms_teams_room)

           # Create Microsoft Teams message content
           ms_teams_connector.color('green')
           ms_teams_connector.title('Starting: ' + str(self.limit))
           ms_teams_connector.text('Starting ' + str(self.playbook_name) + ' on: ' + str(self.limit))

           # Create section card with more facts (key/value)
           ms_teams_card_obj = pymsteams.cardsection()
           ms_teams_card_obj.disableMarkdown()
           ms_teams_card_obj.title('Ansible Information')
           ms_teams_card_obj.addFact('Executed by', str(self.executor))
           ms_teams_card_obj.addFact('Playbook', str(self.playbook_name))
           ms_teams_card_obj.addFact('Limit(s)', str(self.limit))
           ms_teams_card_obj.addFact('Tag(s)', str(self.tags))
           ms_teams_card_obj.addFact('Extra-Vars', str(self.extra_vars))

           # Add section to teams message
           ms_teams_connector.addSection(ms_teams_card_obj)

           # Send message to Microsoft Teams chat channel
           # (honor dry-run mode)
           if self.ms_teams_notify:
               ms_teams_connector.send()
           else:
               ms_teams_connector.printme()
       except:
           print '\n[CRITICAL]: Could not connect to Microsoft Teams.'


   def teams_send_msg_fin(self):
       """
       Fuction to send finished task messages to defined Microsoft
       Teams chat channel with additional run information.
       """
       try:
           # Create Microsoft Teams connection object
           ms_teams_connector = pymsteams.connectorcard(self.ms_teams_room)

           # Create Microsoft Teams message content
           ms_teams_connector.color('green')
           ms_teams_connector.title('Finished: ' + str(self.host))
           ms_teams_connector.text('Sucessfully executed ' + str(self.playbook_name) + ' on: ' + str(self.host))

           # Create section card with more facts (key/value)
           ms_teams_card_obj = pymsteams.cardsection()
           ms_teams_card_obj.disableMarkdown()
           ms_teams_card_obj.title('Ansible Information')
           ms_teams_card_obj.addFact('Executed by', str(self.executor))
           ms_teams_card_obj.addFact('Hosts', str(self.hosts))
           ms_teams_card_obj.addFact('Playbook', str(self.playbook_name))
           ms_teams_card_obj.addFact('Limit(s)', str(self.limit))
           ms_teams_card_obj.addFact('Tag(s)', str(self.tags))
           ms_teams_card_obj.addFact('Extra-Vars', str(self.extra_vars))
           ms_teams_card_obj.addFact('Tasks ok', str(self.summary['ok']))
           ms_teams_card_obj.addFact('Tasks unreachable', str(self.summary['unreachable']))
           ms_teams_card_obj.addFact('Tasks skipped', str(self.summary['skipped']))
           ms_teams_card_obj.addFact('Tasks failed', str(self.summary['failures']))
           ms_teams_card_obj.addFact('Duration', str(datetime.timedelta(seconds=self.duration_time.seconds)) + ' h')

           # Add section to teams message
           ms_teams_connector.addSection(ms_teams_card_obj)

           # Send message to Microsoft Teams chat channel
           # (honor dry-run mode)
           if self.ms_teams_notify:
               ms_teams_connector.send()
           else:
               ms_teams_connector.printme()
       except:
           print '\n[CRITICAL]: Could not connect to Microsoft Teams.'
