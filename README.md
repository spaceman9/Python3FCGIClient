
Python FastCGI Client
---------------------
A Python3 FastCGI Client that can directly access a FastCGI web resource


Based on code created by:
https://github.com/wuyunfeng/Python-FastCGI-Client


Usage (First start the FastCGI Process)
---------------------------------------

    from FastCGIClient import *
    client = FastCGIClient('127.0.0.1', 9000, 3000, 0)
	params = dict()
	documentRoot = "/Users/baidu/php_workspace"
	uri = "/echo.php"
	content = "name=john&address=beijing"
	params = {'GATEWAY_INTERFACE': 'FastCGI/1.0',
          'REQUEST_METHOD': 'POST',
          'SCRIPT_FILENAME': documentRoot + uri,
          'SCRIPT_NAME': uri,
          'QUERY_STRING': '',
          'REQUEST_URI': uri,
          'DOCUMENT_ROOT': documentRoot,
          'SERVER_SOFTWARE': 'php/fcgiclient',
          'REMOTE_ADDR': '127.0.0.1',
          'REMOTE_PORT': '9985',
          'SERVER_ADDR': '127.0.0.1',
          'SERVER_PORT': '80',
          'SERVER_NAME': "localhost",
          'SERVER_PROTOCOL': 'HTTP/1.1',
          'CONTENT_TYPE': 'application/x-www-form-urlencoded',
          'CONTENT_LENGTH': len(content)
          }
	client.request(params, content)

Unix Socket
-----------
The example code above uses a tcp socket. 
It is also possible to connect to the fast CGI server using a unix socket.
Change the hostname to a file path starting with /.  The port is ignored.

    client = FastCGIClient('/var/run/php-fpm/www.sock', 0, 3000, 0)


See also the Fast CGI specification at:
https://fastcgi-archives.github.io
