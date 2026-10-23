#!/usr/bin/env python3
"""Verify shared Redis sessions and R2 attachments across two HTTP replicas."""
import argparse
import json
import urllib.request


def post(url, path, params, cookie=None):
    headers = {'Content-Type': 'application/json'}
    if cookie:
        headers['Cookie'] = cookie
    body = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': params}).encode()
    request = urllib.request.Request(url + path, body, headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response, json.loads(response.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--first', default='http://127.0.0.1:8069')
    parser.add_argument('--second', default='http://127.0.0.1:8068')
    parser.add_argument('--db', default='test_ci')
    options = parser.parse_args()

    response, result = post(options.first, '/web/session/authenticate', {
        'db': options.db, 'login': 'admin', 'password': 'admin',
    })
    assert result.get('result', {}).get('uid'), result
    cookie = response.headers['Set-Cookie'].split(';', 1)[0]

    _, session = post(options.second, '/web/session/get_session_info', {}, cookie)
    assert session.get('result', {}).get('uid') == result['result']['uid'], session

    request = urllib.request.Request(
        options.second + '/web/image/res.company/1/favicon',
        headers={'Cookie': cookie},
    )
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    with opener.open(request, timeout=30) as response:
        favicon = response.read()
        assert response.status == 200 and favicon, response.status

    print(json.dumps({
        'shared_session': True,
        'shared_attachment': True,
        'uid': session['result']['uid'],
        'attachment_bytes': len(favicon),
    }))


if __name__ == '__main__':
    main()
