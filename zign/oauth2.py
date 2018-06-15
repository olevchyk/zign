import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse


SUCCESS_PAGE = '''<!DOCTYPE HTML>
<html lang="en-US">
  <head>
    <title>Authentication Successful - Zign</title>
    <style>
        body {
            font-family: sans-serif;
        }
    </style>
  </head>
  <body>
    <p>You are now authenticated with Zign.</p>
    <p>The authentication flow has completed. You may close this window.</p>
  </body>
</html>'''

EXTRACT_TOKEN_PAGE = '''<!DOCTYPE HTML>
<html lang="en-US">
  <head>
    <title>Redirecting...</title>
    <style>
        body {{
            font-family: sans-serif;
        }}
        #error {{
            color: red;
        }}
    </style>
    <script>
        (function extractFragmentQueryString() {{
            function post(url, body, successCb, errorCb) {{
                function noop() {{}}
                function successCb(){{
                    window.location.href = "http://localhost:{port}/?success";
                }}
                function errorCb(){{
                    window.location.href = "http://localhost:{port}/?error";
                }}
                var success = successCb || noop;
                var error = errorCb || noop;
                var req = new XMLHttpRequest();
                req.open("POST", url, true);
                req.setRequestHeader("Content-Type", "application/json");
                req.onreadystatechange = function() {{
                    if (req.readyState === XMLHttpRequest.DONE) {{
                        if (req.status >= 200 && req.status < 300) {{
                          success(req);
                        }} else {{
                          error(req);
                        }}
                    }}
                }}
                req.send(JSON.stringify(body));
            }}

            function displayError(message) {{
              var errorElement = document.getElementById("error");
              errorElement.textContent = message || "Unknown error";
            }}

            function parseQueryString(qs) {{
                return qs.split("&")
                        .reduce(function (result, param) {{
                          var split = param.split("=");
                          if (split.length === 2) {{
                            var key = decodeURIComponent(split[0]);
                            var val = decodeURIComponent(split[1]);
                            result[key] = val;
                          }}
                          return result;
                        }}, {{}});
            }}
            var query = window.location.hash.substring(1);
            var params = parseQueryString(query);
            if (params.access_token) {{
                post("http://localhost:{port}", params, null, function error() {{
                    displayError("Error: Could not POST to server.")
                }});
            }} else {{
                displayError("Error: No access_token in URL.")
            }}
        }})();
    </script>
  </head>
  <body>
    <noscript>
        <p>Your browser does not support Javascript! Please enable it or switch to a Javascript enabled browser.</p>
    </noscript>
    <p>Redirecting...</p>
    <p id="error"></p>
  </body>
</html>'''

ERROR_PAGE = '''<!DOCTYPE HTML>
<html lang="en-US">
  <head>
    <title>Authentication Failed - Zign</title>
  </head>
  <body>
    <p><font face=arial>The authentication flow did not complete successfully. Please try again. You may close this
    window.</font></p>
  </body>
</html>'''


class ClientRedirectHandler(BaseHTTPRequestHandler):
    '''Handles OAuth 2.0 redirect and return a success page if the flow has completed.'''

    def _set_headers(self, content_type='text/html'):
        '''Sets initial response headers of the request.'''
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.end_headers()

    def do_POST(self):
        '''Handle the POST request from the redirect.
        Parses the token from the query parameters and returns a success page if the flow has completed'''
        self._set_headers("application/json")

        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        self.server.__tokeninfo = json.loads(self.data_string)
        if 'access_token' in self.server.__tokeninfo.keys():
            self.wfile.write('{"status": "success"}'.encode('utf-8'))
        else:
            self.send_error(500, json.dumps(self.server.__tokeninfo).encode('utf-8'))

    def do_GET(self):
        '''Handle initial GET request display EXTRACT_TOKEN_PAGE
        On succesfull post XMLHttpRequest - displays SUCCESS_PAGE
        '''
        query_string = urlparse(self.path).query
        self._set_headers()

        if not query_string:
            self.wfile.write(EXTRACT_TOKEN_PAGE.format(port=self.server.server_port).encode('utf-8'))
        elif 'success' in query_string:
            self.server.query_params = self.server.__tokeninfo
            self.wfile.write(SUCCESS_PAGE.encode('utf-8'))
        else:
            self.wfile.write(ERROR_PAGE.encode('utf-8'))

    def log_message(self, format, *args):
        """Do not log messages to stdout while running as cmd. line program."""


class ClientRedirectServer(HTTPServer):
    """A server to handle OAuth 2.0 redirects back to localhost.

    Waits for a single request and parses the query parameters
    into query_params and then stops serving.
    """
    query_params = {}
    __tokeninfo = {}

    def __init__(self, address):
        super().__init__(address, ClientRedirectHandler)
