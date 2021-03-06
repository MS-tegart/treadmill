"""Treadmill openldap bootstrap.
"""

import pkgutil

from .. import aliases

__path__ = pkgutil.extend_path(__path__, __name__)


DEFAULTS = {
    'dir_config': '{{ dir }}/etc/openldap',
    'dir_schema': '{{ dir_config }}/schema',
    'attribute_options': ['tm-'],
    'backends': [{'name': '{0}config',
                  'owner': '{{owner}}',
                  'rootdn': 'cn=Manager,cn=config',
                  'rootpw': '{{ rootpw }}',
                  'suffix': 'cn=config'},
                 {'name': '{1}mdb',
                  'objectclass': 'olcMdbConfig',
                  'owner': '{{owner}}',
                  'rootdn': 'cn=Manager,cn=config',
                  'suffix': '{{ suffix }}'}],
    'log_levels': [16384],
    'schemas': ['file://{{ openldap }}/etc/openldap/schema/core.ldif']
}

ALIASES = aliases.ALIASES
