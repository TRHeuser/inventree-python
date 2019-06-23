"""
The inventree_api module handles low level requests and authentication
with the InvenTree database server.
"""


import requests
from requests.auth import HTTPBasicAuth
import os
import json
import logging


class InvenTreeAPI(object):
    """ Basic class for performing Inventree API requests.

    GET - Fetch data from the server

    """

    def __init__(self, base_url, **kwargs):
        """ Initialize class with initial parameters

        Args:
            base_url - Base API URL
            
        kwargs:
            username - Login username
            password - Login password
            token - Authentication token (if provided, username/password are ignored)
            use_token_auth - Use token authentication? (Default = True)
        """

        if not base_url.endswith('/'):
            base_url += '/'

        self.base_url = base_url

        self.username = kwargs.get('username', None)
        self.password = kwargs.get('password', None)
        self.token = kwargs.get('token', None)
        self.use_token_auth = kwargs.get('use_token_auth', True)

        if self.use_token_auth:
            if not self.token:
                self.requestToken()
        else:
            # Basic authentication
            self.auth = HTTPBasicAuth(self.username, self.password)

    def requestToken(self):
        """ Return authentication token from the server """

        if not self.username or not self.password:
            raise AttributeError('Supply username and password to request token')

        print("Requesting auth token from server...")

        # Request an auth token from the server
        token_url = os.path.join(self.base_url, 'user/token/')
        print(token_url)
        reply = requests.post(token_url, json = {
            'username': self.username,
            'password': self.password,
        })

        try:
            self.token = json.loads(reply.text)['token']
            print("... Success!")
        except:
            print("Could not retrieve token from server")
            self.token = None      

    def request(self, url, **kwargs):
        """ Perform a URL request to the Inventree API """

        # Remove leading slash
        if url.startswith('/'):
            url = url[1:]

        api_url = os.path.join(self.base_url, url)

        if not api_url.endswith('/'):
            api_url += '/'

        method = kwargs.get('method', 'get')

        params = kwargs.get('params', {})

        json = kwargs.get('json', {})

        headers = kwargs.get('headers', {})

        search_term = kwargs.get('search', None)

        if search_term is not None:
            params['search'] = search_term

        methods = {
            'GET': requests.get,
            'POST': requests.post,
            'PUT': requests.put,
            'DELETE': requests.delete,
        }

        if method.upper() not in methods.keys():
            logging.error("Unknown request method '{m}'".format(m=method))
            return None

        method = method.upper()

        if self.use_token_auth and self.token:
            headers['Authentication'] = 'Token {t}'.format(t=self.token)
            auth=None
        else:
            auth=self.auth

        try:
            response = methods[method](
                api_url,
                auth=auth,
                params=params,
                headers=headers,
                json=json
            )

        except requests.exceptions.ConnectionError:
            logging.error("Connection refused - '{url}'".format(url=api_url))
            return None

        if response is None:
            logging.error("Null response - {method} '{url}'".format(method=method, url=api_url))
            return None

        logging.info("Request: {method} {url} - {response}".format(method=method, url=api_url, response=response.status_code))

        # Detect invalid response codes
        # Anything 300+ is 'bad'
        if response.status_code >= 300:
            logging.warning("Bad response ({code}) - {method} '{url}'".format(code=response.status_code, method=method, url=api_url))

        # A delete request won't return JSON formatted data (ignore further checks)
        if method == 'DELETE':
            return response

        ctype = response.headers.get('content-type')

        if not ctype == 'application/json':
            logging.error("'Response content-type is not JSON - '{url}' - '{f}'".format(url=api_url, f=ctype))
            return None

        return response

    def delete(self, url, **kwargs):
        """ Perform a DELETE request. Used to remove a record in the database.

        """

        headers = {'content-type': 'application/json'}

        response = self.request(url, method='delete', headers=headers, **kwargs)

        if response is None:
            return False

        print(response.status_code, response.text)

    def post(self, url, data, **kwargs):
        """ Perform a POST request. Used to create a new record in the database.

        Args:
            url - API endpoint URL
            data - JSON data to create new object
        """

        headers = {'content-type': 'application/json'}

        params = {
            'format': 'json',
        }

        response = self.request(url, json=data, method='post', headers=headers, params=params, **kwargs)

        if response is None:
            return False

        if response.status_code in [200, 201]:
            return True
        else:
            logging.error("POST request failed at '{url}' - {status}".format(url=url, status=response.status_code))
            return False

    def put(self, url, data, **kwargs):
        """ Perform a PUT request. Used to update existing records in the database.

        Args:
            url - API endpoint URL
            data - JSON data to PUT
        """

        headers = {'content-type': 'application/json'}

        params = {
            'format': 'json',
        }

        response = self.request(url, json=data, method='put', headers=headers, params=params, **kwargs)

        if response is None:
            return None
        
        if response.status_code == 200:
            return True
        else:
            logging.error("PUT request failed at '{url}' - {status}".format(url=url, status=response.status_code))
            return False

    def get(self, url, **kwargs):
        """ Perform a GET request

        Args:
            url - API url

        kwargs:

        """

        response = self.request(url, method='get', **kwargs)

        # No response returned
        if response is None:
            return None

        try:
            data = json.loads(response.text)
        except json.decoder.JSONDecodeError:
            logging.error("Error decoding JSON response - '{url}'".format(url=url))
            return None

        return data
