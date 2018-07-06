from __future__ import absolute_import, division, print_function, unicode_literals

from pando import Response
import requests

from liberapay.exceptions import LazyResponse

from liberapay.elsewhere._base import PlatformOAuth2, logger
from liberapay.elsewhere._extractors import key
from liberapay.elsewhere._paginators import header_links_paginator
from liberapay.elsewhere._utils import extract_domain_from_url


class Mastodon(PlatformOAuth2):

    # Platform attributes
    name = 'mastodon'
    display_name = 'Mastodon'
    account_url = 'https://{domain}/users/{user_name}'
    single_domain = False

    def example_account_address(self, _):
        return _('example@mastodon.social')

    # Auth attributes
    # Mastodon uses https://github.com/doorkeeper-gem/doorkeeper
    auth_url = 'https://{domain}/oauth/authorize'
    access_token_url = 'https://{domain}/oauth/token'
    can_auth_with_client_credentials = True

    # API attributes
    # https://github.com/tootsuite/documentation/blob/master/Using-the-API/API.md
    api_format = 'json'
    api_paginator = header_links_paginator()
    api_url = 'https://{domain}/api/v1'
    api_user_info_path = '/accounts/{user_id}'
    # api_user_name_info_path = '/search?q={user_name}@{domain}'
    api_user_self_info_path = '/accounts/verify_credentials'
    api_friends_path = '/accounts/{user_id}/following'
    ratelimit_headers_prefix = 'x-ratelimit-'

    # User info extractors
    x_domain = key('url', clean=extract_domain_from_url)
    x_user_id = key('id')
    x_user_name = key('username')
    x_display_name = key('display_name')
    x_avatar_url = key('avatar_static')
    x_description = key('note')

    def x_user_info(self, extracted, info, default):
        if 'accounts' in info:
            accounts = info.get('accounts')
            if accounts:
                return accounts[0]
            raise Response(404)
        return default

    def register_app(self, domain):
        data = {
            'client_name': self.app_name,
            'redirect_uris': self.callback_url.format(domain=domain),
            'scopes': 'read',
            'website': self.app_url,
        }
        r = requests.post('https://%s/api/v1/apps' % domain, data, timeout=self.api_timeout)
        status = r.status_code
        try:
            o = r.json()
            c_id, c_secret = o['client_id'], o['client_secret']
        except (KeyError, ValueError):
            c_id, c_secret = None, None
        if status != 200 or not c_id or not c_secret:
            logger.error('{} responded with {}:\n{}'.format(domain, status, r.text))
            msg = lambda _: _(
                "Is {0} really a {1} server? It is currently not acting like one.",
                domain, self.display_name,
            )
            raise LazyResponse(502, msg)
        return c_id, c_secret
