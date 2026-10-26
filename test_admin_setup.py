import unittest
from unittest.mock import patch
from starlette.requests import Request
from fastapi import HTTPException
import main

class AdminSetupTests(unittest.TestCase):
    def setUp(self):
        self.current = {'admin_token': '', 'global_tunnel_token': 'private-tunnel', 'trust_tailscale_admin': False, 'trust_lan_admin': False}
        for patcher in (patch('main.settings.load_settings', side_effect=lambda: dict(self.current)), patch('main.settings.save_settings', side_effect=lambda data: self.current.update(data)), patch('main.scanner.scan_library'), patch('main.run_server.get_local_ips', return_value=['192.168.1.9'])):
            patcher.start()
            self.addCleanup(patcher.stop)

    def request(self, ip='192.168.1.50', headers=None):
        return Request({'type': 'http', 'client': (ip, 12345), 'headers': [(k.encode(), v.encode()) for k, v in (headers or {}).items()], 'query_string': b''})

    def test_local_setup_password_and_remove(self):
        result = main.update_settings(main.UpdateSettingsRequest(admin_token='my-password'), self.request())
        self.assertTrue(result['admin_password_set'])
        self.assertNotIn('admin_token', result)
        self.assertFalse(main.is_host_admin(self.request()))
        self.assertFalse(main.is_host_admin(self.request(headers={'x-admin-token': 'wrong'})))
        main.update_settings(main.UpdateSettingsRequest(admin_token=''), self.request(headers={'x-admin-token': 'my-password'}))
        self.assertTrue(main.is_host_admin(self.request()))

    def test_public_settings_hide_secrets(self):
        response = main.get_all_settings()
        self.assertNotIn('admin_token', response)
        self.assertNotIn('global_tunnel_token', response)
        self.assertFalse(response['admin_password_set'])

    def test_no_password_does_not_open_remote_setup(self):
        for request in (self.request('8.8.8.8'), self.request(headers={'cf-connecting-ip': '8.8.8.8'}), self.request(headers={'x-forwarded-for': '192.168.1.50'})):
            with self.assertRaises(HTTPException) as error:
                main.update_settings(main.UpdateSettingsRequest(admin_token='takeover'), request)
            self.assertEqual(error.exception.status_code, 403)

if __name__ == '__main__':
    unittest.main()
