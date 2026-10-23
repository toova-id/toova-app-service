# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import optparse
import sys
from pathlib import Path

import odoo

from . import Command


class Storage(Command):
    """Audit external attachment storage without modifying data"""

    def run(self, args):
        parser = odoo.tools.config.parser
        parser.prog = f'{Path(sys.argv[0]).name} {self.name}'
        group = optparse.OptionGroup(parser, 'Storage audit')
        group.add_option('--storage-limit', dest='storage_limit', type='int', default=0,
                         help='Stop after this many S3 attachment rows; 0 audits all rows.')
        group.add_option('--include-orphans', action='store_true', default=False,
                         help='Also list unreferenced objects under this database prefix.')
        parser.add_option_group(group)
        options = odoo.tools.config.parse_config(args)
        dbname = odoo.tools.config['db_name']
        if not dbname:
            parser.error('storage command requires exactly one database with -d')
        if ',' in dbname:
            parser.error('storage command accepts exactly one database')
        if odoo.tools.config['attachment_store'] != 's3':
            parser.error('storage command currently requires attachment_store=s3')

        registry = odoo.registry(dbname)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            domain = [
                ('store_fname', '=like', 's3://%'),
                '|', ('res_field', '=', False), ('res_field', '!=', False),
            ]
            attachments = env['ir.attachment'].sudo().search(
                domain, order='id', limit=options.storage_limit,
            )
            client = attachments._s3_client()
            bucket = odoo.tools.config['s3_bucket']
            missing = []
            unavailable = []
            seen = set()
            checked_objects = 0
            for attachment in attachments:
                key = attachment._s3_key(attachment.store_fname)
                if key in seen:
                    continue
                seen.add(key)
                checked_objects += 1
                try:
                    client.head_object(Bucket=bucket, Key=key)
                except Exception as error:
                    classified = attachment._s3_error(error, attachment.store_fname, 'audit')
                    if isinstance(classified, odoo.exceptions.MissingError):
                        missing.append({'attachment_id': attachment.id, 'key': key})
                    else:
                        unavailable.append({
                            'attachment_id': attachment.id,
                            'key': key,
                            'error': str(classified),
                        })

            orphans = []
            if options.include_orphans:
                prefix = '/'.join(part for part in (
                    odoo.tools.config['s3_prefix'].strip('/'), dbname,
                ) if part) + '/'
                continuation_token = None
                while True:
                    parameters = {'Bucket': bucket, 'Prefix': prefix}
                    if continuation_token:
                        parameters['ContinuationToken'] = continuation_token
                    try:
                        page = client.list_objects_v2(**parameters)
                    except Exception as error:
                        unavailable.append({
                            'key': prefix,
                            'error': str(attachments._s3_error(error, prefix, 'list')),
                        })
                        break
                    orphans.extend(
                        obj['Key'] for obj in page.get('Contents', ())
                        if obj['Key'] not in seen
                    )
                    if not page.get('IsTruncated'):
                        break
                    continuation_token = page['NextContinuationToken']

        result = {
            'database': dbname,
            'attachment_rows': len(attachments),
            'unique_objects': checked_objects,
            'missing_objects': missing,
            'orphan_objects': orphans,
            'unavailable_objects': unavailable,
            'ok': not missing and not unavailable,
        }
        print(json.dumps(result, sort_keys=True))
        if not result['ok']:
            sys.exit(1)
