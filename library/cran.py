#!/usr/bin/env python

# Copyright (c) 2018, Florian Paul Hoberg <florian.hoberg@credativ.de>

from ansible.module_utils.basic import *

DOCUMENTATION = '''
---
module: cran
short_description: Manages packapges for Microsoft R
description:
  - This module adds support to manage additional packages for Microsoft R
    also known as "cran".
    To run this module you need to have Microsoft R Open installed.
options:
  state:
    description:
      - Adds/removes a package from CRAN
    options:
      - present
      - absent
  package:
    description:
      - Wildcard package name (e.g. 'vioplot')
  repository:
    description:
      - Define a custom CRAN repository
    default: https://cran.rstudio.com/
author:
- Florian Paul Hoberg <florian.hoberg@credativ.de>
'''
EXAMPLES = '''
- name: Install CRAN module vioplot 
  cran:
    state: present
    package: vioplot
- name: Install custom CRAN module foo 
  cran:
    state: present
    package: foo
    repository: https://files.hoberg.ch/cran/ 
'''

MSR_BINARY = "/usr/bin/Rscript"


def list_package_cran(module, package):
    """ List package from cran """
    rc, out, err = module.run_command("%s --slave -e 'p <- installed.packages(); cat(p[p[,1] == \"%s\",1])'" 
                                      % (MSR_BINARY, package))
    if out == package: 
        package = True
        return package
    else:
        package = False
        return package
    if not rc is 0:
        module.fail_json(msg="Error: " + str(err))


def add_package_cran(module, package, repository):
    """ Add package from cran """
    rc, out, err = module.run_command("%s --slave -e 'install.packages(pkgs=\"%s\", repos=\"%s\")'" 
                                      % (MSR_BINARY, package, repository))
    if rc is 0: 
        changed = True
        return changed
    else:
        module.fail_json(msg="Error: " + str(err))


def remove_package_cran(module, package):
    """ Remove package from cran """
    rc, out, err = module.run_command("%s --slave -e 'remove.packages(pkgs=\"%s\")'" 
                                      % (MSR_BINARY, package))
    if rc is 0: 
        changed = True
        return changed
    else:
        module.fail_json(msg="Error: " + str(err))


def main():
    """ Start main program to add/remove a package from cran """
    module = AnsibleModule(
        argument_spec     = dict(
            state         = dict(required=True,  type='str'),
            package       = dict(required=True,  type='str'),
            repository    = dict(required=False, type='str', default='https://cran.rstudio.com/'),
        ),
        supports_check_mode=True
    )


    state        = module.params['state']
    package      = module.params['package']
    repository   = module.params['repository']
    changed = False

    # Check if package is already installed
    cran_package = list_package_cran(module, package)

    # Add a package from CRAN
    if state == "present":
        if not cran_package:
            changed = add_package_cran(module, package, repository)

    # Remove a package from CRAN 
    if state == "absent":
        if cran_package:
            changed = remove_package_cran(module, package)

    # Create Ansible meta output
    response = {"package": package, "state": state}
    if changed is True:
        module.exit_json(changed=True, meta=response)
    else:
        module.exit_json(changed=False, meta=response)

if __name__ == '__main__':
    main()
