#!/usr/bin/env python3
"""Check storage audit failure semantics against invalid credentials and outage."""
import argparse
import json
import os
import subprocess


def run(command, env=None):
    return subprocess.run(command, capture_output=True, text=True, env=env)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', default='odoo16-engine:test')
    parser.add_argument('--network', default='docker_default')
    parser.add_argument('--config', default='docker/odoo.conf')
    parser.add_argument('--env-file', default='docker/.env.r2')
    options = parser.parse_args()
    config = os.path.abspath(options.config)
    env_file = os.path.abspath(options.env_file)
    base = [
        'docker', 'run', '--rm', '--network', options.network,
        '-v', f'{config}:/etc/odoo/odoo.conf:ro',
        '--entrypoint', '/opt/odoo/odoo-bin', options.image,
        'storage', '--config=/etc/odoo/odoo.conf', '-d', 'test_ci',
        '--no-http', '--log-level=error', '--storage-limit=1',
    ]

    docker_prefix = base[:7]
    docker_suffix = base[7:]
    invalid = run(docker_prefix + [
        '-e', 'AWS_ACCESS_KEY_ID=invalid',
        '-e', 'AWS_SECRET_ACCESS_KEY=invalid',
        '-e', 'AWS_DEFAULT_REGION=auto',
        '-e', 'AWS_EC2_METADATA_DISABLED=true',
    ] + docker_suffix)
    assert invalid.returncode == 1, invalid.stderr
    invalid_result = json.loads(invalid.stdout.strip().splitlines()[-1])
    assert not invalid_result['ok'] and invalid_result['unavailable_objects']

    outage = run(
        docker_prefix + ['--env-file', env_file] + docker_suffix +
        ['--s3-endpoint-url=http://127.0.0.1:1']
    )
    assert outage.returncode == 1, outage.stderr
    outage_result = json.loads(outage.stdout.strip().splitlines()[-1])
    assert not outage_result['ok'] and outage_result['unavailable_objects']

    print(json.dumps({'bad_credentials': 'pass', 'outage': 'pass'}))


if __name__ == '__main__':
    main()
