#!/usr/bin/python

import socket
import random


class FastCGIClient:
    """A Fast-CGI Client for Python"""

    # private
    __FCGI_VERSION = 1

    __FCGI_ROLE_RESPONDER = 1
    __FCGI_ROLE_AUTHORIZER = 2
    __FCGI_ROLE_FILTER = 3

    __FCGI_TYPE_BEGIN = 1
    __FCGI_TYPE_ABORT = 2
    __FCGI_TYPE_END = 3
    __FCGI_TYPE_PARAMS = 4
    __FCGI_TYPE_STDIN = 5
    __FCGI_TYPE_STDOUT = 6
    __FCGI_TYPE_STDERR = 7
    __FCGI_TYPE_DATA = 8
    __FCGI_TYPE_GETVALUES = 9
    __FCGI_TYPE_GETVALUES_RESULT = 10
    __FCGI_TYPE_UNKOWNTYPE = 11

    __FCGI_HEADER_SIZE = 8

    # request state
    FCGI_STATE_SEND = 1
    FCGI_STATE_ERROR = 2
    FCGI_STATE_SUCCESS = 3

    def __init__(self, host, port, timeout, keepalive):
        self.host = host
        self.port = port
        self.timeout = timeout
        if keepalive:
            self.keepalive = 1
        else:
            self.keepalive = 0
        self.sock = None
        self.requests = dict()

    def __connect(self):
        if self.host[0] == '/':
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                self.sock.connect(self.host)
            except socket.error as msg:
                self.sock.close()
                self.sock = None
                print(repr(msg))
                return False
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # if self.keepalive:
            #     self.sock.setsockopt(socket.SOL_SOCKET, socket.SOL_KEEPALIVE, 1)
            # else:
            #     self.sock.setsockopt(socket.SOL_SOCKET, socket.SOL_KEEPALIVE, 0)
            try:
                self.sock.connect((self.host, int(self.port)))
            except socket.error as msg:
                self.sock.close()
                self.sock = None
                print(repr(msg))
                return False
        return True

    def __encodeFastCGIRecord(self, fcgi_type, content, requestid):
        length = len(content)
        return bytes([
            FastCGIClient.__FCGI_VERSION,
            fcgi_type,
            (requestid >> 8) & 0xFF,
            requestid & 0xFF,
            (length >> 8) & 0xFF,
            length & 0xFF,
            0,
            0]) + content

    def __encodeNameValueParams(self, name, value):
        name = str(name).encode()
        value = str(value).encode()
        nLen = len(name)
        vLen = len(value)
        record = bytearray()
        if nLen < 128:
            record += bytes([nLen])
        else:
            record += bytes([(nLen >> 24) | 0x80, (nLen >> 16) & 0xFF, (nLen >> 8) & 0xFF, nLen & 0xFF])
        if vLen < 128:
            record += bytes([vLen])
        else:
            record += bytes([(vLen >> 24) | 0x80, (vLen >> 16) & 0xFF, (vLen >> 8) & 0xFF, vLen & 0xFF])
        return record + name + value

    def __decodeFastCGIHeader(self, stream):
        header = dict()
        header['version'] = int(stream[0])
        header['type'] = int(stream[1])
        header['requestId'] = (int(stream[2]) << 8) | int(stream[3])
        header['contentLength'] = (int(stream[4]) << 8) | int(stream[5])
        header['paddingLength'] = int(stream[6])
        header['reserved'] = int(stream[7])
        return header

    def __decodeFastCGIRecord(self):
        header = self.sock.recv(int(FastCGIClient.__FCGI_HEADER_SIZE))
        if not header:
            return False
        else:
            record = self.__decodeFastCGIHeader(header)
            record['content'] = ''
            content = bytearray()
            if 'contentLength' in record.keys():
                contentLength = record['contentLength']
                buffer = self.sock.recv(contentLength)
                while contentLength and buffer:
                    contentLength -= len(buffer)
                    content += buffer
            record['content'] = bytes(content)
            if 'paddingLength' in record.keys():
                if record['paddingLength'] > 0:
                    skiped = self.sock.recv(record['paddingLength'])
            return record

    def request(self, nameValuePairs={}, post=''):
        if not self.__connect():
            print('connect failure! please check your fasctcgi-server !!')
            return

        requestId = random.randint(1, (1 << 16) - 1)
        self.requests[requestId] = dict()
        request = bytearray()

        beginFCGIRecordContent = bytes([0, FastCGIClient.__FCGI_ROLE_RESPONDER, int(self.keepalive), 0, 0, 0, 0, 0])
        request += self.__encodeFastCGIRecord(FastCGIClient.__FCGI_TYPE_BEGIN, beginFCGIRecordContent, requestId)

        paramsRecord = bytearray()
        if nameValuePairs:
            for (name, value) in iter(nameValuePairs.items()):
                paramsRecord += self.__encodeNameValueParams(name, value)

        if paramsRecord:
            request += self.__encodeFastCGIRecord(FastCGIClient.__FCGI_TYPE_PARAMS, paramsRecord, requestId)
        request += self.__encodeFastCGIRecord(FastCGIClient.__FCGI_TYPE_PARAMS, b'', requestId)

        if post:
            request += self.__encodeFastCGIRecord(FastCGIClient.__FCGI_TYPE_STDIN, post, requestId)
        request += self.__encodeFastCGIRecord(FastCGIClient.__FCGI_TYPE_STDIN, b'', requestId)

        self.sock.send(request)
        self.requests[requestId]['state'] = FastCGIClient.FCGI_STATE_SEND
        self.requests[requestId]['error'] = ''
        self.requests[requestId]['response'] = ''
        return self.__waitForResponse(requestId)

    def __waitForResponse(self, requestId):
        while True:
            response = self.__decodeFastCGIRecord()
            print(response)
            if not response:
                self.requests[requestId]['state'] = FastCGIClient.FCGI_STATE_ERROR
                break
            if response['type'] == FastCGIClient.__FCGI_TYPE_END:
                self.requests[requestId]['application_status'] = \
                    int(response['content'][1]) << 24 | \
                    int(response['content'][2]) << 16 | \
                    int(response['content'][3]) <<  8 | \
                    int(response['content'][4])
                self.requests[requestId]['protocol_status'] = int(response['content'][5])
                self.requests[requestId]['state'] = FastCGIClient.FCGI_STATE_SUCCESS
                break
            if response['type'] == FastCGIClient.__FCGI_TYPE_STDERR:
                self.requests[requestId]['state'] = FastCGIClient.FCGI_STATE_ERROR
                self.requests['error'] += response['content'].decode('utf-8','ignore')
            if response['type'] == FastCGIClient.__FCGI_TYPE_STDOUT:
                self.requests[requestId]['response'] += response['content'].decode('utf-8','ignore')
        return self.requests[requestId]['response']

    def __repr__(self):
        return "fastcgi connect host:{} port:{}".format(self.host, self.port)
