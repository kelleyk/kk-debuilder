import re
import csv
from six import text_type
from io import StringIO as TextIO   # XXX: Py2 equivalent?

import arrow


DEFAULT_UBUNTU_DISTRO_INFO_PATH = '/usr/share/distro-info/ubuntu.csv'


class DistroVersion(dict):
    def __init__(self, *args, **kwargs):
        super(DistroVersion, self).__init__(*args, **kwargs)
        
        assert set(self) == set('version,codename,series,created,release,eol,eol-server'.split(','))
        assert all(((k == 'eol-server' and v is None) or v == v.strip())
                   for k, v in self.items())
        # 'codename' might be e.g. 'Trusty Tahr'; 'series' will be e.g. 'trusty'.  'series' is
        # roughly synonymous with distribution or release.
        assert re.match(r'^[a-z]+$', self.series)

        # Convert these to dates.
        for key in ('created', 'release', 'eol', 'eol-server'):
            v = self[key]
            if v is not None:
                self[key] = arrow.get(v).date()
        
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            key = key.replace('_', '-')
            return self[key]

    @property
    def numeric_version(self):
        # Convert e.g. '14.04 LTS' to '14.04'.
        v = self.version.split()[0]
        assert re.match(r'^\d+(\.\d+)+$', v)
        return v

    @property
    def supported(self):
        return self.eol >= arrow.utcnow().date()

    @property
    def supported_server(self):
        # e.g. 'warty' does not list separate EOL date
        eol_server = self.eol if self.eol_server is None else self.eol_server
        return eol_server >= arrow.utcnow().date()

    @property
    def released(self):
        return self.release < arrow.utcnow().date()
    
    
def get_ubuntu_distro_info(path=DEFAULT_UBUNTU_DISTRO_INFO_PATH):
    with open(path, 'r') as f:
        return parse_distro_info(f.read())

        
def parse_distro_info(data):
    if not isinstance(data, text_type):
        data = data.decode('utf-8')
        
    reader = csv.DictReader(TextIO(data))
    return (DistroVersion(row) for row in reader)


if __name__ == '__main__':
    from pprint import pprint as pp
    for v in get_ubuntu_distro_info():
        pp(v)
        pp({k: getattr(v, k) for k in ('supported', 'supported_server', 'released')})
        print('')
