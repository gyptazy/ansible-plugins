#!/usr/bin/python
#
# Copyright: (c) 2013, RSD Services S.A
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: java_cert
version_added: '2.4'
short_description: Uses keytool to import/remove key from java keystore(cacerts)
description:
  - This is a wrapper module around keytool. Which can be used to import/remove
    certificates from a given java keystore.
options:
  cert_url:
    description:
      - Basic URL to fetch SSL certificate from. One of cert_url or cert_path is required to load certificate.
  cert_port:
    description:
      - Port to connect to URL. This will be used to create server URL:PORT
    default: 443
  cert_path:
    description:
      - Local path to load certificate from. One of cert_url or cert_path is required to load certificate.
  cert_alias:
    description:
      - Imported certificate alias.
  trust_cacert:
    description:
      - Trust imported cert as CAcert
    default: False
    version_added: "2.6"
  pkcs12_path:
    description:
      - Local path to load PKCS12 keystore from.
    version_added: "2.4"
  pkcs12_password:
    description:
      - Password for importing from PKCS12 keystore.
    default: ''
    version_added: "2.4"
  force_update:
    description:
      - Forces overwrite of a certificate with an existing alias name.
    default: False
    version_added: "2.8"
  pkcs12_alias:
    description:
      - Alias in the PKCS12 keystore.
    default: 1
    version_added: "2.4"
  keystore_path:
    description:
      - Path to keystore.
  keystore_pass:
    description:
      - Keystore password.
    required: true
  keystore_create:
    description:
      - Create keystore if it doesn't exist
  executable:
    description:
      - Path to keytool binary if not used we search in PATH for it.
    default: keytool
  state:
    description:
      - Defines action which can be either certificate import or removal.
    choices: [ absent, present ]
    default: present
author:
- Adam Hamsik (@haad)
- Florian Paul Azim Hoberg (@gyptazy)
'''

EXAMPLES = '''
- name: Import SSL certificate from google.com to a given cacerts keystore
  java_cert:
    cert_url: google.com
    cert_port: 443
    keystore_path: /usr/lib/jvm/jre7/lib/security/cacerts
    keystore_pass: changeit
    state: present
- name: Remove certificate with given alias from a keystore
  java_cert:
    cert_url: google.com
    keystore_path: /usr/lib/jvm/jre7/lib/security/cacerts
    keystore_pass: changeit
    executable: /usr/lib/jvm/jre7/bin/keytool
    state: absent
- name: Import trusted CA from SSL certificate
  java_cert:
    cert_path: /opt/certs/rootca.crt
    keystore_path: /tmp/cacerts
    keystore_pass: changeit
    keystore_create: yes
    state: present
    cert_alias: LE_RootCA
    trust_cacert: True
- name: Import SSL certificate from google.com to a keystore, create it if it doesn't exist
  java_cert:
    cert_url: google.com
    keystore_path: /tmp/cacerts
    keystore_pass: changeit
    keystore_create: yes
    state: present
- name: Import a pkcs12 keystore with a specified alias, create it if it doesn't exist
  java_cert:
    pkcs12_path: "/tmp/importkeystore.p12"
    cert_alias: default
    keystore_path: /opt/wildfly/standalone/configuration/defaultkeystore.jks
    keystore_pass: changeit
    keystore_create: yes
    state: present
'''

RETURN = '''
msg:
  description: Output from stdout of keytool command after execution of given command.
  returned: success
  type: string
  sample: "Module require existing keystore at keystore_path '/tmp/test/cacerts'"
rc:
  description: Keytool command execution return value
  returned: success
  type: int
  sample: "0"
cmd:
  description: Executed command to get action done
  returned: success
  type: string
  sample: "keytool -importcert -noprompt -keystore"
'''

import os

# import module snippets
from ansible.module_utils.basic import AnsibleModule


def check_cert_present(module, executable, keystore_path, keystore_pass, alias):
    ''' Check if certificate with alias is present in keystore
        located at keystore_path '''
    test_cmd = ("%s -noprompt -list -keystore '%s' -storepass '%s' "
                "-alias '%s'") % (executable, keystore_path, keystore_pass, alias)

    (check_rc, _, _) = module.run_command(test_cmd)
    if check_rc == 0:
        return True
    return False


def import_cert_url(module, executable, url, port, keystore_path, keystore_pass, alias, trust_cacert):
    ''' Import certificate from URL into keystore located at keystore_path '''
    import re

    https_proxy = os.getenv("https_proxy")
    no_proxy = os.getenv("no_proxy")

    proxy_opts = ''
    if https_proxy is not None:
        (proxy_host, proxy_port) = https_proxy.split(':')
        proxy_opts = ("-J-Dhttps.proxyHost=%s -J-Dhttps.proxyPort=%s") % (proxy_host, proxy_port)

        if no_proxy is not None:
            # For Java's nonProxyHosts property, items are separated by '|',
            # and patterns have to start with "*".
            non_proxy_hosts = no_proxy.replace(',', '|')
            non_proxy_hosts = re.sub(r'(^|\|)\.', r'\1*.', non_proxy_hosts)

            # The property name is http.nonProxyHosts, there is no
            # separate setting for HTTPS.
            proxy_opts += (" -J-Dhttp.nonProxyHosts='%s'") % (non_proxy_hosts)

    fetch_cmd = ("%s -printcert -rfc -sslserver %s %s:%d") % (executable, proxy_opts, url, port)

    import_cmd = ("%s -importcert -noprompt -keystore '%s' "
                  "-storepass '%s' -alias '%s'") % (executable, keystore_path,
                                                    keystore_pass, alias)
    if trust_cacert:
        import_cmd = import_cmd + " -trustcacerts"

    if module.check_mode:
        module.exit_json(changed=True)

    # Fetch SSL certificate from remote host.
    (_, fetch_out, _) = module.run_command(fetch_cmd, check_rc=True)

    # Use remote certificate from remote host and import it to a java keystore
    (import_rc, import_out, import_err) = module.run_command(import_cmd,
                                                             data=fetch_out,
                                                             check_rc=False)
    diff = {'before': '\n', 'after': '%s\n' % alias}
    if import_rc == 0:
        return module.exit_json(changed=True, msg=import_out,
                                rc=import_rc, cmd=import_cmd, stdout=import_out,
                                diff=diff)
    else:
        return module.fail_json(msg=import_out, rc=import_rc, cmd=import_cmd,
                                error=import_err)


def import_cert_path(module, executable, path, keystore_path, keystore_pass, alias, trust_cacert):
    ''' Import certificate from path into keystore located on
        keystore_path as alias '''

    import_cmd = ("%s -importcert -noprompt -keystore '%s' "
                  "-storepass '%s' -file '%s' -alias '%s'") % (executable,
                                                               keystore_path,
                                                               keystore_pass,
                                                               path, alias)

    if trust_cacert:
        import_cmd = import_cmd + " -trustcacerts"

    if module.check_mode:
        module.exit_json(changed=True)

    # Use local certificate from local path and import it to a java keystore
    (import_rc, import_out, import_err) = module.run_command(import_cmd,
                                                             check_rc=False)

    diff = {'before': '\n', 'after': '%s\n' % alias}
    if import_rc == 0:
        return module.exit_json(changed=True, msg=import_out,
                                rc=import_rc, cmd=import_cmd, stdout=import_out,
                                error=import_err, diff=diff)
    else:
        return module.fail_json(msg=import_out, rc=import_rc, cmd=import_cmd)


def import_pkcs12_path(module, executable, path, keystore_path, keystore_pass, pkcs12_pass, pkcs12_alias, alias):
    ''' Import pkcs12 from path into keystore located on
        keystore_path as alias '''
    import_cmd = ("%s -importkeystore -noprompt -destkeystore '%s' -srcstoretype PKCS12 "
                  "-deststorepass '%s' -destkeypass '%s' -srckeystore '%s' -srcstorepass '%s' "
                  "-srcalias '%s' -destalias '%s'") % (executable, keystore_path, keystore_pass,
                                                       keystore_pass, path, pkcs12_pass, pkcs12_alias, alias)

    if module.check_mode:
        module.exit_json(changed=True)

    # Use local certificate from local path and import it to a java keystore
    (import_rc, import_out, import_err) = module.run_command(import_cmd,
                                                             check_rc=False)

    diff = {'before': '\n', 'after': '%s\n' % alias}
    if import_rc == 0:
        return module.exit_json(changed=True, msg=import_out,
                                rc=import_rc, cmd=import_cmd, stdout=import_out,
                                error=import_err, diff=diff)
    else:
        return module.fail_json(msg=import_out, rc=import_rc, cmd=import_cmd)


def delete_cert(module, executable, keystore_path, keystore_pass, alias, module_exit=False):
    ''' Delete certificate identified with alias from keystore on keystore_path '''
    del_cmd = ("%s -delete -keystore '%s' -storepass '%s' "
               "-alias '%s'") % (executable, keystore_path, keystore_pass, alias)

    if module.check_mode:
        module.exit_json(changed=True)

    # Delete SSL certificate from keystore
    (del_rc, del_out, del_err) = module.run_command(del_cmd, check_rc=True)

    diff = {'before': '%s\n' % alias, 'after': None}

    # Check if module will need to exit
    if not module_exit:
        return module.exit_json(changed=True, msg=del_out,
                                rc=del_rc, cmd=del_cmd, stdout=del_out,
                                error=del_err, diff=diff)


def test_keytool(module, executable):
    ''' Test if keytool is actuall executable or not '''
    test_cmd = "%s" % (executable)

    module.run_command(test_cmd, check_rc=True)


def test_keystore(module, keystore_path):
    ''' Check if we can access keystore as file or not '''
    if keystore_path is None:
        keystore_path = ''

    if not os.path.exists(keystore_path) and not os.path.isfile(keystore_path):
        # Keystore doesn't exist we want to create it
        return module.fail_json(changed=False,
                                msg="Module require existing keystore at keystore_path '%s'"
                                    % (keystore_path))


def main():
    argument_spec = dict(
        cert_url=dict(type='str'),
        cert_path=dict(type='path'),
        pkcs12_path=dict(type='path'),
        pkcs12_password=dict(type='str', no_log=True),
        pkcs12_alias=dict(type='str'),
        cert_alias=dict(type='str'),
        force_update=dict(type='bool', default=False),
        cert_port=dict(type='int', default='443'),
        keystore_path=dict(type='path'),
        keystore_pass=dict(type='str', required=True, no_log=True),
        trust_cacert=dict(type='bool', default=False),
        keystore_create=dict(type='bool', default=False),
        executable=dict(type='str', default='keytool'),
        state=dict(type='str', default='present', choices=['absent', 'present']),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=[['cert_path', 'cert_url', 'pkcs12_path']],
        required_together=[['keystore_path', 'keystore_pass']],
        mutually_exclusive=[
            ['cert_url', 'cert_path', 'pkcs12_path']
        ],
        supports_check_mode=True,
    )

    url = module.params.get('cert_url')
    path = module.params.get('cert_path')
    port = module.params.get('cert_port')

    pkcs12_path = module.params.get('pkcs12_path')
    pkcs12_pass = module.params.get('pkcs12_password', '')
    pkcs12_alias = module.params.get('pkcs12_alias', '1')

    force_update = module.params.get('force_update')
    cert_alias = module.params.get('cert_alias') or url
    trust_cacert = module.params.get('trust_cacert')

    keystore_path = module.params.get('keystore_path')
    keystore_pass = module.params.get('keystore_pass')
    keystore_create = module.params.get('keystore_create')
    executable = module.params.get('executable')
    state = module.params.get('state')

    if path and not cert_alias:
        module.fail_json(changed=False,
                         msg="Using local path import from %s requires alias argument."
                             % (keystore_path))

    test_keytool(module, executable)

    if not keystore_create:
        test_keystore(module, keystore_path)

    cert_present = check_cert_present(module, executable, keystore_path,
                                      keystore_pass, cert_alias)

    if state == 'absent':
        if cert_present:
            delete_cert(module, executable, keystore_path, keystore_pass, cert_alias)

    elif state == 'present':
        if pkcs12_path:
            if not cert_present:
                import_pkcs12_path(module, executable, pkcs12_path, keystore_path,
                                   keystore_pass, pkcs12_pass, pkcs12_alias, cert_alias)
            else:
                if force_update:
                    delete_cert(module, executable, keystore_path, keystore_pass, cert_alias, force_update)
                    import_pkcs12_path(module, executable, pkcs12_path, keystore_path,
                                       keystore_pass, pkcs12_pass, pkcs12_alias, cert_alias)
                    module.exit_json(changed=True)
                else:
                    module.fail_json(changed=False,
                                     msg="Certificate alias %s is already present. Use force_update to overwrite."
                                     % (cert_alias))

        if path:
            if not cert_present:
                import_cert_path(module, executable, path, keystore_path,
                             keystore_pass, cert_alias, trust_cacert)
            else:
                if force_update:
                    delete_cert(module, executable, keystore_path, keystore_pass, cert_alias, force_update)
                    import_cert_path(module, executable, path, keystore_path,
                                     keystore_pass, cert_alias, trust_cacert)
                    module.exit_json(changed=True)
                else:
                    module.fail_json(changed=False,
                                     msg="Certificate alias %s is already present. Use force_update to overwrite."
                                     % (cert_alias))

        if url:
            if not cert_present:
                import_cert_url(module, executable, url, port, keystore_path,
                                keystore_pass, cert_alias, trust_cacert)
            else:
                if force_update:
                    delete_cert(module, executable, keystore_path, keystore_pass, cert_alias, force_update)
                    import_cert_url(module, executable, url, port, keystore_path,
                                    keystore_pass, cert_alias, trust_cacert)
                    module.exit_json(changed=True)
                else:
                    module.fail_json(changed=False,
                                     msg="Certificate alias %s is already present. Use force_update to overwrite."
                                     % (cert_alias))


    module.exit_json(changed=False)


if __name__ == "__main__":
    main()
