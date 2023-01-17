#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2018, Florian Paul Azim Hoberg @gyptazy <gyptazy@gyptazy.ch>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: freshclam
version_added: 2.8
short_description: Update ClamAV signatures with freshclam
description:
     - This module updates ClamAV signatures with freschlam. Freshclam needs to be present.
options:
  update:
    description:
      - Whether to update ClamAV signatures
    choices: [ True, False ]
    default: True 
# informational: requirements for nodes
requirements:
- clamav
- freshclam
author:
    - Florian Paul Azim Hoberg (@gyptazy)
'''

EXAMPLES = '''
- name: Update ClamAV signatures
  freshclam:
    update: True
'''

RETURN = '''
meta:
    update: Successfully updated ClamAV signatures via freshclam.
'''

from ansible.module_utils.basic import AnsibleModule


def get_freshclam_path(module):
    """ Get path to freshclam """
    try:
        freshclam_binary = module.get_bin_path('freshclam')
        if freshclam_binary.endswith('freshclam'):
            return freshclam_binary
    except AttributeError:
        module.fail_json(msg='Error: Could not find path to freshclam binary. Make sure freshclam is installed.')


def update_freshclam(module, freshclam_binary):
    """ Run freshclam to update ClamAV signatures """
    rc_code, out, err = module.run_command("%s" % (freshclam_binary))
    return rc_code, out, err


def main():
    """ Start main program to run freschlam """
    module = AnsibleModule(
        argument_spec=dict(
            update=dict(type='bool', default=True),
        ),
        supports_check_mode=True
    )

    update = module.params['update']
    changed = False

    # Get path of freshclam
    freshclam = get_freshclam_path(module)

    # Update ClamAV signatures via freshclam
    if update:
        rc_code, out, err = update_freshclam(module, freshclam)

    # Create Ansible meta output
    if rc_code == 0:
        response = {'update': 'Successfully updated ClamAV signatures via freshclam.'}
        module.exit_json(changed=True, meta=response)

    if rc_code == 1:
        response = {'update': 'ClamAV signatures are already up to date.'}
        module.exit_json(changed=False, meta=response)

    if rc_code == 2:
        # make sure we catch stdout and stderr
        module.fail_json(msg='Error: ' + str(out) + str(err))

if __name__ == '__main__':
    main()
