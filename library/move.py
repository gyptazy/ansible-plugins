#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2018, Florian Paul Hoberg <florian.hoberg@credativ.de>
# Written by Florian Paul Hoberg <florian.hoberg@credativ.de>

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: move
version_added: 2.9
short_description: File movement (mv) for Linux/Unix
description:
     - This module provides support for file/directory movement for Linux/Unix systems if possible.
        If it isn't possible to move a file, it will be copied and the source deleted. 
options:
  src:
    description:
      - Source file/directory to move or rename
  dst:
    description:
      - Destination path or name of file/directory.
    choices: [ present, absent ]
    default: present
# informational: requirements for nodes
requirements:
- python module 'shutil' 
author:
    - '"Florian Paul Hoberg (@florianpaulhoberg)" <florian.hoberg@credativ.de>'
'''

EXAMPLES = '''
- name: Move file to another position on filesystem
  move:
    src: /etc/hosts 
    dst: /etc/backup/hosts 
'''

from ansible.module_utils.basic import AnsibleModule
import os
import json
try:
    import shutil
except ImportError:
    print(json.dumps({
    "failed" : True,
    "msg"    : "Error: Python module 'shutil' is missing."
    }))
    sys.exit(1)


def test_file(module, src):
    """ Test if src file is present """
    file = os.path.exists(src)
    return file


def move_file(module, src, dst):
    """ Move file to another position in filesystem """
    shutil.move(src, dst)
    changed = True
    return changed


def main():
    """ Start main program to add/remove a package from cran """
    module = AnsibleModule(
        argument_spec=dict(
            src=dict(required=True, type='str'),
            dst=dict(required=True, type='str'),
        ),
        supports_check_mode=True
    )

    src = module.params['src']
    dst = module.params['dst']
    changed = False

    file = test_file(module, src)
    if file:
        changed = move_file(module, src, dst)

    # Create Ansible meta output
    response = {'Sourcefile': src, 'Destfile': dst}
    module.exit_json(changed=changed, meta=response)


if __name__ == '__main__':
    main()
