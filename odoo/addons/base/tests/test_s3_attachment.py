# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError
from werkzeug.exceptions import ServiceUnavailable

from odoo import tools
from odoo.exceptions import AccessError, MissingError
from odoo.http import Stream
from odoo.tests.common import TransactionCase
from odoo.addons.base.models import ir_attachment
from odoo.addons.base.models.ir_attachment import IrAttachment


class TestS3Attachment(TransactionCase):

    @staticmethod
    def _client_error(status, code):
        return ClientError({
            'ResponseMetadata': {'HTTPStatusCode': status},
            'Error': {'Code': code, 'Message': code},
        }, 'GetObject')

    def test_s3_errors_are_classified(self):
        attachment = self.env['ir.attachment']
        self.assertIsInstance(
            attachment._s3_error(self._client_error(404, 'NoSuchKey'), 's3://missing', 'read'),
            MissingError,
        )
        self.assertIsInstance(
            attachment._s3_error(self._client_error(403, 'AccessDenied'), 's3://denied', 'read'),
            AccessError,
        )
        self.assertIsInstance(
            attachment._s3_error(NoCredentialsError(), 's3://denied', 'read'),
            AccessError,
        )
        self.assertIsInstance(
            attachment._s3_error(
                EndpointConnectionError(endpoint_url='https://example.invalid'),
                's3://offline', 'read',
            ),
            ServiceUnavailable,
        )
        self.assertIsInstance(
            attachment._s3_error(self._client_error(503, 'SlowDown'), 's3://offline', 'read'),
            ServiceUnavailable,
        )

    def test_s3_client_is_reused(self):
        client = MagicMock()
        with patch.dict(tools.config.options, {
            's3_endpoint_url': 'https://example.invalid', 's3_region': 'auto',
        }), patch.dict(ir_attachment._s3_clients, {}, clear=True), \
             patch('boto3.client', return_value=client) as make_client:
            attachment = self.env['ir.attachment']
            self.assertIs(attachment._s3_client(), client)
            self.assertIs(attachment._s3_client(), client)
        make_client.assert_called_once_with(
            's3', endpoint_url='https://example.invalid', region_name='auto',
        )

    def test_s3_download_url(self):
        attachment = self.env['ir.attachment'].new({
            'name': 'image.png', 'mimetype': 'image/png',
            'store_fname': 's3://aa/' + 'a' * 40,
        })
        client = MagicMock()
        client.generate_presigned_url.return_value = 'https://signed.example/object'
        with patch.object(IrAttachment, '_s3_client', return_value=client), \
             patch.dict(tools.config.options, {
                 's3_bucket': 'attachments', 's3_prefix': 'odoo',
                 's3_download_url_seconds': 300,
             }):
            self.assertEqual(attachment._s3_download_url(), 'https://signed.example/object')
        client.generate_presigned_url.assert_called_once_with(
            'get_object', Params={
                'Bucket': 'attachments',
                'Key': f'odoo/{self.env.cr.dbname}/aa/' + 'a' * 40,
                'ResponseContentType': 'image/png',
                'ResponseContentDisposition': "inline; filename*=UTF-8''image.png",
            }, ExpiresIn=300,
        )

    def test_s3_attachment_stream_does_not_use_filestore(self):
        attachment = self.env['ir.attachment'].new({
            'name': 'image.png', 'mimetype': 'image/png',
            'store_fname': 's3://aa/' + 'a' * 40,
        })
        stream = Stream.from_attachment(attachment)
        self.assertEqual(stream.type, 'url')
        self.assertIs(stream.attachment, attachment)
        self.assertIsNone(stream.path)

    def test_s3_css_asset_stream_keeps_odoo_origin(self):
        attachment = self.env['ir.attachment'].new({
            'name': 'web.assets.min.css', 'mimetype': 'text/css',
            'url': '/web/assets/1-deadbeef/web.assets.min.css',
            'store_fname': 's3://aa/' + 'a' * 40,
        })
        with patch.object(IrAttachment, '_file_read', return_value=b'@font-face{}'):
            stream = Stream.from_attachment(attachment)
        self.assertEqual(stream.type, 'data')
        self.assertEqual(stream.data, b'@font-face{}')
        self.assertIsNone(stream.path)

    def test_s3_roundtrip(self):
        objects = {}

        class S3Client:
            def put_object(client, Bucket, Key, Body, IfNoneMatch):
                self.assertEqual(IfNoneMatch, '*')
                objects[(Bucket, Key)] = Body

            def get_object(client, Bucket, Key):
                return {'Body': io.BytesIO(objects[(Bucket, Key)])}

        attachment = self.env['ir.attachment']
        with patch.object(IrAttachment, '_storage', return_value='s3'), \
             patch.object(IrAttachment, '_s3_client', return_value=S3Client()), \
             patch.dict(tools.config.options, {'s3_bucket': 'attachments', 's3_prefix': 'odoo'}):
            fname = attachment._file_write(b'hello', 'a' * 40)
            self.assertEqual(fname, 's3://aa/' + 'a' * 40)
            self.assertEqual(attachment._file_read(fname), b'hello')

    def test_s3_delete_runs_after_commit(self):
        callbacks = self.env.cr.postcommit._funcs
        before = len(callbacks)
        self.env['ir.attachment']._file_delete('s3://aa/' + 'a' * 40)
        self.assertEqual(len(callbacks), before + 1)
        callbacks.pop()

    def test_s3_delete_reference_check_includes_binary_fields(self):
        fname = 's3://aa/' + 'a' * 40
        attachment = self.env['ir.attachment']
        callbacks = self.env.cr.postcommit._funcs
        before = len(callbacks)
        attachment._file_delete(fname)
        self.assertEqual(len(callbacks), before + 1)
        callback = callbacks.pop()
        cursor_context = MagicMock()
        cursor = cursor_context.__enter__.return_value
        cursor.fetchone.return_value = (1,)
        with patch.object(self.env.registry, 'cursor', return_value=cursor_context), \
             patch.object(IrAttachment, '_s3_client') as s3_client:
            callback()
        cursor.execute.assert_called_once_with(
            'SELECT 1 FROM ir_attachment WHERE store_fname = %s LIMIT 1',
            [fname],
        )
        s3_client.assert_not_called()
