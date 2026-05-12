"""
Local mock SOAP service for ArithmeticOperation demo.
Implements AddInteger and DivideInteger matching the crcind.com interface.
No external dependencies — pure Python stdlib.

Listens on two ports to match the WSO2 MI endpoint config:
  9292 → NumberAdditionEP
  9393 → NumberDivisionEP

Run: python3 service.py
"""

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import xml.etree.ElementTree as ET

PORTS = [9292, 9393]
SOAP_NS = 'http://schemas.xmlsoap.org/soap/envelope/'
TEMPURI_NS = 'http://tempuri.org'


def find_int(parent, name):
    node = parent.find(f'{{{TEMPURI_NS}}}{name}')
    if node is None:
        node = parent.find(name)
    if node is None or node.text is None:
        raise ValueError(f"Missing element: {name}")
    return int(node.text)


def soap_response(operation, result):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
        '<soapenv:Body>'
        f'<{operation}Response xmlns="{TEMPURI_NS}">'
        f'<{operation}Result>{result}</{operation}Result>'
        f'</{operation}Response>'
        '</soapenv:Body>'
        '</soapenv:Envelope>'
    )


def soap_fault(message):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
        '<soapenv:Body>'
        '<soapenv:Fault>'
        '<faultcode>soapenv:Server</faultcode>'
        f'<faultstring>{message}</faultstring>'
        '</soapenv:Fault>'
        '</soapenv:Body>'
        '</soapenv:Envelope>'
    )


class SOAPHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        content_length = self.headers.get('Content-Length')
        transfer_enc = self.headers.get('Transfer-Encoding', '').lower()

        if content_length and int(content_length) > 0:
            body = self.rfile.read(int(content_length))
        elif 'chunked' in transfer_enc:
            body = b''
            while True:
                size_line = self.rfile.readline().rstrip(b'\r\n')
                if not size_line:
                    continue
                try:
                    chunk_size = int(size_line, 16)
                except ValueError:
                    break
                if chunk_size == 0:
                    break
                body += self.rfile.read(chunk_size)
                self.rfile.read(2)  # trailing CRLF
        else:
            body = b''

        response_body = self._handle(body)
        encoded = response_body.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/xml; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _handle(self, body):
        try:
            root = ET.fromstring(body)
            soap_body = root.find(f'{{{SOAP_NS}}}Body')
            if soap_body is None:
                return soap_fault('Missing SOAP Body')

            for child in soap_body:
                tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

                if tag == 'AddInteger':
                    arg1 = find_int(child, 'Arg1')
                    arg2 = find_int(child, 'Arg2')
                    result = arg1 + arg2
                    print(f"  AddInteger({arg1}, {arg2}) = {result}")
                    return soap_response('AddInteger', result)

                if tag == 'DivideInteger':
                    arg1 = find_int(child, 'Arg1')
                    arg2 = find_int(child, 'Arg2')
                    if arg2 == 0:
                        return soap_fault('Division by zero')
                    result = arg1 // arg2
                    print(f"  DivideInteger({arg1}, {arg2}) = {result}")
                    return soap_response('DivideInteger', result)

            return soap_fault('Unknown operation')

        except Exception as e:
            print(f"  ERROR: {e}")
            return soap_fault(str(e))

    def do_GET(self):
        msg = b'SOAP Arithmetic Service is running'
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)

    def log_message(self, fmt, *args):
        pass


def start_server(port):
    server = HTTPServer(('0.0.0.0', port), SOAPHandler)
    server.serve_forever()


if __name__ == '__main__':
    for port in PORTS[:-1]:
        t = threading.Thread(target=start_server, args=(port,), daemon=True)
        t.start()
        print(f"  Listening on http://localhost:{port}/  (AddInteger)")

    last_port = PORTS[-1]
    print(f"  Listening on http://localhost:{last_port}/  (DivideInteger)")
    print("Waiting for requests... (Ctrl+C to stop)\n")
    try:
        start_server(last_port)
    except KeyboardInterrupt:
        print("\nStopped.")
