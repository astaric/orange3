import cgi
from http.server import BaseHTTPRequestHandler
import io
import json
import pickle
import logging
import shutil
import socketserver

from Orange.server.commands import Create, Call, Get, Command
import uuid

cache = {}


class Promise:
    def __init__(self, id):
        self.id = id

    def get(self, id):
        return cache[id]

    def ready(self, id):
        return id in cache


class Proxy:
    __id__ = None

    def __init__(self, id):
        self.__id__ = id


class ExecutionFailedError(Exception):
    pass


class OrangeServer(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        super(OrangeServer, self).__init__(request, client_address, server)

    def do_GET(self):
        resource_id = self.path.strip("/")

        if resource_id not in cache:
            return self.send_error(404, "Resource {} not found".format(resource_id))

        buf = pickle.dumps(cache[resource_id])
        f = io.BytesIO(buf)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", "attachment;filename={}.pickle"
                                                .format(resource_id))
        self.send_header("Content-Length", str(len(buf)))
        self.end_headers()

        shutil.copyfileobj(f, self.wfile)
        f.close()

    def do_POST(self):
        result_id = str(uuid.uuid1())
        try:
            data = self.parse_post_data()
            if isinstance(data, Command):
                result = self.execute_command(data)
                cache[result_id] = result
            else:
                cache[result_id] = data
        except AttributeError as err:
            return self.send_error(400, str(err))
        except ExecutionFailedError as err:
            return self.send_error(500, str(err))
        except ValueError as err:
            return self.send_error(400, str(err))

        encoded = result_id.encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))

        self.end_headers()

        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        shutil.copyfileobj(f, self.wfile)
        f.close()

    def parse_post_data(self):
        content_len = int(self.headers['content-length'] or 0)
        content_type = self.headers.get_content_type()
        data = self.rfile.read(content_len)

        if content_type == 'application/octet-stream':
            return pickle.loads(data)
        elif content_type == 'application/json':
            return json.JSONDecoder(object_hook=self.object_hook).decode(data.decode('utf-8'))
        else:
            return data

    @staticmethod
    def object_hook(pairs):
        if 'create' in pairs:
            return Create(**pairs['create'])

        if 'call' in pairs:
            return Call(**pairs['call'])

        if 'get' in pairs:
            return Get(**pairs['get'])

        if '__jsonclass__' in pairs:
            constructor, param = pairs['__jsonclass__']
            if constructor == "Promise":
                return cache[param]

        return pairs

    def process_request(self):
        path = self.path.strip("/")

        post_vars = self.parse_post_data()
        if path == "create":
            return Create(**post_vars)
        elif path == 'call':
            return Call(**post_vars)
        elif path == 'getattr':
            return Get(**post_vars)

    @staticmethod
    def execute_command(command):
        try:
            return command.execute()
        except Exception as err:
            raise ExecutionFailedError(
                "Execution of {} failed with error: {}"
                .format(command, err)) from err


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M')

    PORT = 8000

    Handler = OrangeServer

    httpd = socketserver.TCPServer(("", PORT), Handler)

    print("serving at port", PORT)
    try:
        httpd.serve_forever()
    except Exception as ex:
        httpd.server_close()
