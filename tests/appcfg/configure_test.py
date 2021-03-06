"""
Unit test for treadmill.appcfg.configure
"""

import os
import pwd
import shutil
import tempfile
import unittest

import mock

import treadmill
import treadmill.services

from treadmill.appcfg import configure as app_cfg
from treadmill.apptrace import events


class AppCfgConfigureTest(unittest.TestCase):
    """Tests for teadmill.appcfg.configure"""

    def setUp(self):
        # Access protected module _base_service
        # pylint: disable=W0212
        self.root = tempfile.mkdtemp()
        self.tm_env = mock.Mock(
            apps_dir=os.path.join(self.root, 'apps'),
            cleanup_dir=os.path.join(self.root, 'cleanup'),
            svc_cgroup=mock.Mock(
                spec_set=treadmill.services._base_service.ResourceService,
            ),
            svc_localdisk=mock.Mock(
                spec_set=treadmill.services._base_service.ResourceService,
            ),
            svc_network=mock.Mock(
                spec_set=treadmill.services._base_service.ResourceService,
            ),
        )

    def tearDown(self):
        if self.root and os.path.isdir(self.root):
            shutil.rmtree(self.root)

    @mock.patch('pwd.getpwnam', mock.Mock(auto_spec=True))
    @mock.patch('shutil.copyfile', mock.Mock(auto_spec=True))
    @mock.patch('treadmill.utils.rootdir',
                mock.Mock(return_value='/treadmill'))
    @mock.patch('treadmill.appcfg.manifest.load', auto_spec=True)
    @mock.patch('treadmill.appevents.post', mock.Mock(auto_spec=True))
    @mock.patch('treadmill.subproc.get_aliases', mock.Mock(return_value={}))
    def test_configure(self, mock_load):
        """Tests that appcfg.configure creates necessary s6 layout."""
        manifest = {
            'proid': 'foo',
            'environment': 'dev',
            'shared_network': False,
            'cpu': '100',
            'memory': '100M',
            'disk': '100G',
            'services': [
                {
                    'name': 'web_server',
                    'command': '/bin/true',
                    'restart': {
                        'limit': 5,
                        'interval': 60,
                    },
                },
            ],
            'endpoints': [
                {
                    'name': 'http',
                    'port': '8000',
                },
            ],
            'name': 'proid.myapp#0',
            'uniqueid': 'AAAAA',
        }
        mock_load.return_value = manifest
        app_unique_name = 'proid.myapp-0-00000000AAAAA'
        app_dir = os.path.join(self.root, 'apps', app_unique_name)

        app_cfg.configure(self.tm_env, '/some/event')

        mock_load.assert_called_with(self.tm_env, '/some/event')
        shutil.copyfile.assert_called_with(
            '/some/event',
            os.path.join(app_dir, 'manifest.yml')
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(app_dir, 'run')
            )
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(app_dir, 'finish')
            )
        )
        self.assertTrue(
            os.path.exists(
                os.path.join(app_dir, 'log', 'run')
            )
        )

        treadmill.appevents.post.assert_called_with(
            mock.ANY,
            events.ConfiguredTraceEvent(
                instanceid='proid.myapp#0',
                uniqueid='AAAAA',
                payload=None
            )
        )

    @mock.patch('pwd.getpwnam', mock.Mock(auto_spec=True))
    @mock.patch('shutil.copyfile', mock.Mock(auto_spec=True))
    @mock.patch('treadmill.utils.rootdir',
                mock.Mock(return_value='/treadmill'))
    @mock.patch('treadmill.appcfg.manifest.load', auto_spec=True)
    def test_configure_bad_userid(self, mock_load):
        """Tests that appcfg.configure failure on bad usedid.
        """
        manifest = {
            'proid': 'foo',
            'environment': 'dev',
            'cpu': '100',
            'memory': '100M',
            'disk': '100G',
            'services': [
                {
                    'name': 'web_server',
                    'command': '/bin/true',
                    'restart': {
                        'limit': 5,
                        'interval': 60,
                    },
                },
            ],
            'endpoints': [
                {
                    'name': 'http',
                    'port': '8000',
                },
            ],
            'name': 'proid.myapp#0',
            'uniqueid': '12345',
        }
        mock_load.return_value = manifest
        pwd.getpwnam.side_effect = KeyError

        self.assertRaises(
            KeyError,
            app_cfg.configure,
            self.tm_env,
            '/some/event',
        )
        mock_load.assert_called_with(self.tm_env, '/some/event')
        self.assertFalse(shutil.copyfile.called)


if __name__ == '__main__':
    unittest.main()
