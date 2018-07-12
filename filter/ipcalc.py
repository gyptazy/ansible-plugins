#!/usr/bin/python
# (c) 2018 Florian Paul Hoberg <florian.hoberg@credativ.de>
# Fast and easy filter plugin to check if an IP address is included
# in a given subnet.

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from netaddr import IPNetwork, IPAddress
from ansible import errors

class FilterModule(object):
   def filters(self):
       return {
           'ipcalc': self.ipcalc
       }


   def ipcalc(self, ipaddr, subnet):
       """ This filter checks if an IP address is included in a
           given subnet and will return a book (True/False).
           Usage:
            set_fact: check_network="{{ '10.10.10.2/32' | ipcalc('10.10.10.0/24') }}"
       """
       if IPNetwork(ipaddr) in IPNetwork(subnet):
           return True
       else:
           return False

if __name__ == "__main__":
   print(" This python script is only used as an Ansible \n filter plugin and can not run itself.")
