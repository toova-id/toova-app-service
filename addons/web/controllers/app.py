# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import mimetypes
from pathlib import PurePosixPath

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.service import security
from odoo.tools import file_open

from .utils import ensure_db, is_user_internal


class ManagedApp(http.Controller):
    """Serve product client separately from legacy operator WebClient."""

    @staticmethod
    def _manifest():
        with file_open('web/static/app/manifest.json') as manifest_file:
            return json.load(manifest_file)

    @http.route(['/app', '/app/<path:route>'], type='http', auth='none', sitemap=False)
    def app(self, route=None, **kw):
        ensure_db(redirect='/web/login?redirect=/app')
        if not request.session.uid:
            return request.redirect('/web/login?redirect=/app', 303)
        if not security.check_session(request.session, request.env):
            raise http.SessionExpiredException('Session expired')
        if not is_user_internal(request.session.uid):
            raise AccessError('Internal access required.')

        request.session.touch()
        request.update_env(user=request.session.uid)
        entry = self._manifest()['src/main.tsx']
        assets = {
            'script': '/app-assets/' + entry['file'],
            'styles': ['/app-assets/' + path for path in entry.get('css', [])],
        }
        response = request.render('web.managed_app', assets)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'none'"
        return response

    @http.route('/app-assets/<path:asset>', type='http', auth='none', methods=['GET'], save_session=False)
    def assets(self, asset):
        path = PurePosixPath(asset)
        if path.is_absolute() or '..' in path.parts or path.suffix not in ('.js', '.css', '.map'):
            return request.not_found()
        try:
            with file_open('web/static/app/' + path.as_posix(), 'rb') as asset_file:
                content = asset_file.read()
        except FileNotFoundError:
            return request.not_found()
        return request.make_response(content, [
            ('Content-Type', mimetypes.guess_type(path.name)[0] or 'application/octet-stream'),
            ('Cache-Control', 'no-store, max-age=0'),
            ('X-Content-Type-Options', 'nosniff'),
        ])

    @http.route('/api/v1/session', type='http', auth='user', methods=['GET'])
    def session(self):
        user = request.env.user
        if not user._is_internal():
            raise AccessError('Internal access required.')
        modules = sorted(request.env.registry._init_modules)
        return request.make_json_response({
            'user': {'id': user.id, 'name': user.name, 'login': user.login},
            'company': {'id': user.company_id.id, 'name': user.company_id.name},
            'companies': [
                {'id': company.id, 'name': company.name}
                for company in user.company_ids
            ],
            'modules': modules,
            'csrfToken': request.csrf_token(),
        }, headers=[('Cache-Control', 'no-store')])
