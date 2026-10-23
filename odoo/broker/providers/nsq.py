# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""NSQ TCP transport.

Publishing uses nsqd's native TCP protocol. nsqlookupd is used only for producer
and consumer discovery; messages never use nsqd's HTTP publish endpoint.
"""
import json
import logging
import random
import socket
import struct
import threading

import requests

_logger = logging.getLogger(__name__)

_FRAME_RESPONSE = 0


class NSQProvider:
    """Persistent TCP publisher plus pynsq consumer."""

    def __init__(self, config):
        self.discovery = config['nsq_discovery']
        self.tcp_addresses = self._addresses(config['nsqd_tcp_addresses'])
        self.lookupd_addresses = self._addresses(config['nsqlookupd_http_addresses'])
        self.max_in_flight = config['broker_max_in_flight']
        self._socket = None
        self._address = None
        self._publisher_lock = threading.Lock()
        self._consumer_loop = None

    @staticmethod
    def _addresses(value):
        return [address.strip() for address in (value or '').split(',') if address.strip()]

    @staticmethod
    def _recv_exact(sock, size):
        chunks = []
        while size:
            chunk = sock.recv(size)
            if not chunk:
                raise ConnectionError('NSQ TCP connection closed')
            chunks.append(chunk)
            size -= len(chunk)
        return b''.join(chunks)

    def _read_response(self, sock):
        size = struct.unpack('>l', self._recv_exact(sock, 4))[0]
        frame_type = struct.unpack('>l', self._recv_exact(sock, 4))[0]
        body = self._recv_exact(sock, size - 4)
        if frame_type != _FRAME_RESPONSE or body != b'OK':
            raise ConnectionError(f'NSQ rejected command: {body.decode("utf-8", "replace")}')

    def _lookup_address(self, topic):
        if self.discovery == 'direct':
            return random.choice(self.tcp_addresses)
        errors = []
        for lookupd_address in random.sample(self.lookupd_addresses, len(self.lookupd_addresses)):
            try:
                response = requests.get(
                    lookupd_address.rstrip('/') + '/lookup', params={'topic': topic}, timeout=5,
                )
                if response.status_code == 404:
                    return random.choice(self.tcp_addresses)
                response.raise_for_status()
                producers = response.json().get('producers', [])
                if producers:
                    producer = random.choice(producers)
                    return '%s:%s' % (
                        producer.get('broadcast_address') or producer['hostname'], producer['tcp_port'],
                    )
                errors.append(f'{lookupd_address}: no producer')
            except requests.RequestException as error:
                errors.append(f'{lookupd_address}: {error}')
        raise ConnectionError(f'NSQ lookup failed for {topic}: {"; ".join(errors)}')

    def _connect(self, address):
        if self._socket is not None and self._address == address:
            return self._socket
        self._close_publisher()
        host, port = address.rsplit(':', 1)
        sock = socket.create_connection((host, int(port)), timeout=10)
        sock.settimeout(10)
        sock.sendall(b'  V2')
        identity = json.dumps({'client_id': 'odoo', 'hostname': 'odoo', 'feature_negotiation': False}).encode()
        sock.sendall(b'IDENTIFY\n' + struct.pack('>l', len(identity)) + identity)
        # IDENTIFY returns a JSON response rather than plain OK.
        size = struct.unpack('>l', self._recv_exact(sock, 4))[0]
        frame_type = struct.unpack('>l', self._recv_exact(sock, 4))[0]
        body = self._recv_exact(sock, size - 4)
        if frame_type != _FRAME_RESPONSE:
            sock.close()
            raise ConnectionError(f'NSQ IDENTIFY failed: {body.decode("utf-8", "replace")}')
        self._socket, self._address = sock, address
        return sock

    def _close_publisher(self):
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
        self._socket = self._address = None

    def publish(self, topic, body):
        address = self._lookup_address(topic)
        with self._publisher_lock:
            try:
                sock = self._connect(address)
                sock.sendall(b'PUB ' + topic.encode('ascii') + b'\n' + struct.pack('>l', len(body)) + body)
                self._read_response(sock)
            except Exception:
                self._close_publisher()
                raise

    def consume(self, subscriptions, callback):
        try:
            import nsq
            import tornado.ioloop
        except ImportError as error:
            raise RuntimeError('broker_provider=nsq requires pynsq') from error

        readers = []
        for subscription in subscriptions:
            kwargs = {
                'topic': subscription['physical_topic'],
                'channel': subscription['channel'],
                'message_handler': lambda message, sub=subscription: self._handle(callback, sub, message),
                'max_in_flight': min(subscription['max_in_flight'], self.max_in_flight),
            }
            if self.discovery == 'lookupd':
                # Direct bootstrap creates a new topic/channel without a fake
                # business message; lookupd then supplies the producer set.
                kwargs['lookupd_http_addresses'] = self.lookupd_addresses
                kwargs['nsqd_tcp_addresses'] = self.tcp_addresses
            else:
                kwargs['nsqd_tcp_addresses'] = self.tcp_addresses
            readers.append(nsq.Reader(**kwargs))
        if readers:
            _logger.info('NSQ TCP consumers started for %d subscriptions.', len(readers))
            self._consumer_loop = tornado.ioloop.IOLoop.current()
            self._consumer_loop.start()
        return readers

    @staticmethod
    def _handle(callback, subscription, message):
        message.enable_async()
        callback(subscription, message)
        return True

    def stop(self):
        with self._publisher_lock:
            self._close_publisher()
        if self._consumer_loop is not None:
            self._consumer_loop.add_callback(self._consumer_loop.stop)
