#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2023, Florian Paul Azim Hoberg @gyptazy <gyptazy@gyptazy.ch>
#
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: pf
version_added: 2.0.0
short_description: Manage BSD Packet Filter (pf)
description:
    - This module manages the BSD Packet Filter (pf).
options:
  config:
    description:
      - Path to a pf rule set.
    type: str
    required: true
  action:
    description:
      - If state is C(start), packet filter will be started.
      - If state is C(stop), packet filter will be stopped.
      - If state is C(restart), packet filter will be restarted.
      - If state is C(reload), packet filter will be reloaded/flushed.
    choices: [ 'start', 'stop', 'restart', 'reload' ]
    type: str
    default: reload
  dry_run:
    description:
      - Run pfctl with dry run option (rule set provided in meta output)
    type: bool
notes:
  - Supports only BSD
  - Supports C(check_mode).
requirements:
  - pf
author:
    - Florian Paul Azim Hoberg (@gyptazy)
'''

EXAMPLES = r'''
- name: Start pf
  community.general.pf:
    action: start

- name: Reload pf rule set
  community.general.pf:
    config: /etc/pf.conf
    action: reload
'''

RETURN = r'''
action:
    description: An output of the performed action.
    returned: success
    type: str
    sample: started
rule_set:
    description: An output of the active rule set (only dry-run).
    returned: success
    type: str
    sample: pass in all flags S/SA keep state
'''

from ansible.module_utils.basic import AnsibleModule


def main():
    """ start main program to add/remove a package to yum versionlock"""
    module = AnsibleModule(
        argument_spec=dict(
            config  = dict(required=True, type='str'),
            action  = dict(default='reload', choices=['start', 'stop', 'restart', 'reload']),
            dry_run = dict(default=False, type='bool')
        ),
        supports_check_mode=True
    )

    config   = module.params['config']
    action   = module.params['action']
    dry_run  = module.params['dry_run']
    changed  = False
    out      = "No information available for this action."

    # Validate for a supported OS
    validate(module)
    # Get current status of packet filter (pf)
    active_pf = status_pf(module)

    # Perform user defined actions
    # Start packet filter (pf) only if it is currently not running
    if action == 'start':
        if not active_pf:
            start_pf(module, active_pf)
            changed = True

    # Stop packet filter (pf) only it is currently running
    if action == 'stop':
        if active_pf:
            stop_pf(module, active_pf)
            changed = True

    # Restart of packet filter (pf) can always be performed
    if action == 'restart':
        restart_pf(module, active_pf)
        changed = True

    # Reload/Flush the defined rule set for packet filter (pf)
    # Note: May optionally run in dry run mode and print out
    #       the rule set in Ansible meta output
    if action == 'reload':
        out = reload_pf(module, config, dry_run)
        # Dry run will not modify the system
        if not dry_run:
            changed = True
    

    module.exit_json(
        changed=changed,
        meta={
            "action": action,
            "rule_set": out
        }
    )


def validate(module):
    """ Run basic validations """
    _validate_os(module)
    _validate_pf(module)


def _validate_os(module):
    """ Validate the operating system """
    rc, out, err = module.run_command(['cat', '/etc/os-release'])

    # Validate for a BSD string in output
    if not 'BSD' in out:
        msg_err = 'Error: Unsupported OS. This can only be used on BSD systems.'
        module.fail_json(msg=msg_err)       


def _validate_pf(module):
    """ Validate packet filter (pf) """
    rc, out, err = module.run_command(['ls', '/sbin/pfctl'])

    # Validate exit code
    if rc != 0:
        msg_err = 'Error: Unable to find pfctl binary.'
        module.fail_json(msg=msg_err)


def status_pf(module):
    """ Current status of pf """
    rc, out, err = module.run_command(['service', 'pf', 'status'])

    # Obtain current status of pf
    if 'Enabled' in out:
        return True
    else:
        return False


def start_pf(module, active_pf):
    """ Start packet filter (pf) if not already running """
    exec_opt = 'start'
    error=False

    rc, out, err = module.run_command(['service', 'pf', exec_opt])

    # Validate exit code
    if rc != 0:
        error = True

    # Validate for status change to make sure the action
    # has been performed
    new_active_pf = status_pf(module)
    if new_active_pf == active_pf:
        error = True

    # Exit module on failure of change
    if error:
        msg_err = f'Error: Could not {exec_opt} pf.'
        module.fail_json(msg=msg_err)


def stop_pf(module, active_pf):
    """ Stop packet filter (pf) if not already stopped """
    exec_opt = 'stop'
    error=False

    rc, out, err = module.run_command(['service', 'pf', exec_opt])

    # Validate exit code
    if rc != 0:
        error = True

    # Validate for status change to make sure the action
    # has been performed
    new_active_pf = status_pf(module)
    if new_active_pf == active_pf:
        error = True

    # Exit module on failure of change
    if error:
        msg_err = f'Error: Could not {exec_opt} pf.'
        module.fail_json(msg=msg_err)


def restart_pf(module, active_pf):
    """ Restart packet filter (pf) """
    exec_opt = 'restart'
    error=False

    rc, out, err = module.run_command(['service', 'pf', exec_opt])

    # Validate exit code
    if rc != 0:
        error = True

    # Validate for status change to make sure the action
    # has been performed
    new_active_pf = status_pf(module)
    if new_active_pf != active_pf:
        error = True

    # Exit module on failure of change
    if error:
        msg_err = f'Error: Could not {exec_opt} pf.'
        module.fail_json(msg=msg_err)


def reload_pf(module, config, dry_run):
    """ Restart packet filter (pf) """
    error=False

    if dry_run:
        # Dry run with verbose output
        rc, out, err = module.run_command(['pfctl', '-vnf', config])
    else:
        # Flush rule set and apply new rule set
        rc, out, err = module.run_command(['pfctl', '-f', config])

    # Validate exit code
    if rc != 0:
        error = True
    
    # Exit module on failures
    if error:
        msg_err = f'Error: Could not reload pf.'
        module.fail_json(msg=msg_err)

    return out


if __name__ == '__main__':
    main()
