
import logging
import model
import json
import datetime
import webapp2
import cgi
from google.appengine.api import memcache
from google.appengine.api import channel

def auth_only_api(method):
    # Checks for active Google account session
    def wrapper(self, *args, **kwargs):
        token_str = self.request.get("token", None)
        if token_str is not None:
            user = model.User.getByToken(token_str)

            if user:
                self.user = user
                method(self, *args, **kwargs)
            else:
                # Don't redirect to login page, because this is api request
                self.response.set_status(403)
                # TODO: return error detail
        else:
            # Token is required
            self.response.set_status(400)
            # TODO: return error detail

    return wrapper

def json_response(method):
    def wrapper(self, *args, **kwargs):
        self.response.headers['Content-Type'] = 'application/json'
        data = method(self, *args, **kwargs)
        self.response.write(json.dumps(data))

    return wrapper

def json_request(method):
    def wrapper(self, *args, **kwargs):
        self.request.json_body = json.loads(cgi.escape(self.request.body))
        method(self, *args, **kwargs)

    return wrapper

class AccessibleUsersHandler(webapp2.RequestHandler):
    @auth_only_api
    @json_request
    @json_response
    def post(self, app_name):
        app = model.Application.getByName(self.user, app_name)
        if app == None:
            self.response.set_status(404)
            return {'message': 'application not found: ' + app_name}

        user_email = self.request.json_body["email"]
        target_user = model.User.getByEmail(user_email)
        if target_user == None:
            self.response.set_status(404)
            return {'message': 'user not found: ' + user_email}

        app.allowAccess(target_user)
        return {'message': 'success'}

class AppInfoHandler(webapp2.RequestHandler):
    @auth_only_api
    @json_response
    def get(self, access_key):
        app = model.Application.getByAccessKey(access_key)
        if app == None:
            self.response.set_status(404)
            return {'message': 'application not found: ' + access_key}

        elif not app.isOwner(self.user) and not app.isAccessible(self.user):
            self.response.set_status(403)
            return {'message': 'permission denied'}

        result = app.getInfo()
        return result

class AppChannelInfoHandler(webapp2.RequestHandler):
    @auth_only_api
    @json_response
    def get(self, access_key):
        import random

        # Channel API token
        client_id = access_key + self.user.email + str(random.randint(0,1024))
        channel_token = channel.create_channel(client_id)
        channel_info = {"access_key": access_key, "channel_token": channel_token}
        memcache.set(client_id, channel_info)
        logging.info("client_id: " + client_id )

        return channel_info

class DataHandler(webapp2.RequestHandler):
    @auth_only_api
    @json_response
    def get(self, access_key):
        excludedKinds = self.request.GET.getall('exclude')
        logging.info(excludedKinds)
        limit = self.request.get('limit', 60)

        app = model.Application.getByAccessKey(access_key)
        if app == None:
            self.response.set_status(404)
            return {'message': 'application not found: ' + access_key}

        kinds = [kind for kind in app.kinds if kind not in excludedKinds]

        results = app.getFormattedData(requestedKind=kinds, limit=limit)

        return results

    @auth_only_api
    @json_response
    def post(self, app_name):
        data = self.request.get('data')
        data = json.loads(data)

        app = model.Application.create(self.user, app_name)

        try:
            keys = []
            timestamp = datetime.datetime.now()
            for d in data:
                obj = app.addData(d['kind'], float(d['value']), timestamp)
                keys.append({'key': obj.key.urlsafe()})

        except Exception as e:
            self.response.set_status(400)
            return {'message': e.message}

        # Move to task queue later
        channel_tokens = memcache.get(app.getAccessKey())
        if channel_tokens is not None and type(channel_tokens) is list:
            for channel_token in channel_tokens:
                logging.info(channel_token)
                # Implement partial update in future, maybe
                channel.send_message(channel_token, "Graph is updated")

        return keys

class AppHandler(webapp2.RequestHandler):
    @auth_only_api
    @json_response
    def delete(self, access_key):
        app = model.Application.getByAccessKey(access_key)
        if app == None:
            self.response.set_status(404)
            return {'message': 'application not found: ' + access_key}

        app.delete()

        return {'result':True}


app = webapp2.WSGIApplication([
        webapp2.Route('/api/v1/<app_name>/accessible-users/', handler=AccessibleUsersHandler, name='accessibleUsersApi'),
        webapp2.Route('/api/v1/<access_key>/info/', handler=AppInfoHandler, name='appInfoApi'),
        webapp2.Route('/api/v1/<access_key>/channel-info/', handler=AppChannelInfoHandler, name='appChannelInfoApi'),
        webapp2.Route('/api/v1/<access_key>/data/', handler=DataHandler, name='dataApi', methods=['GET']),
        webapp2.Route('/api/v1/<app_name>/data/', handler=DataHandler, name='dataApi', methods=['POST']),
        webapp2.Route('/api/v1/<access_key>/', handler=AppHandler, name='appApi', methods=['DELETE']),
], debug=True)