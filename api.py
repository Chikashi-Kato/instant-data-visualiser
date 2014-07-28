
import logging
import model
import json
import datetime
import webapp2

def auth_only_api(method):
    # Checks for active Google account session
    def wrapper(self, *args, **kwargs):
        token_str = self.request.get("token", None)
        logging.info(token_str)
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

class AppInfoHandler(webapp2.RequestHandler):
    @auth_only_api
    @json_response
    def get(self, app_name):
        app = model.Application.getByName(self.user, app_name)
        if app == None:
            self.response.set_status(404)
            return {'message': 'application not found: ' + app_name}

        result = app.getInfo()
        return result

class DataHandler(webapp2.RequestHandler):
    @auth_only_api
    @json_response
    def get(self, app_name):
        excludedKinds = self.request.GET.getall('exclude')
        logging.info(excludedKinds)
        limit = self.request.get('limit', 60)

        app = model.Application.getByName(self.user, app_name)
        if app == None:
            self.response.set_status(404)
            return {'message': 'application not found: ' + app_name}

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

        return keys

class DataKindHandler(webapp2.RequestHandler):
    @auth_only_api
    @json_response
    def get(self, app_name, kind):
        limit = self.request.get('limit', 60)

        app = model.Application.getByName(self.user, app_name)
        if app == None:
            self.response.set_status(404)
            return {'message': 'application not found: ' + app_name}

        return app.getFormattedData(requestedKind=[kind], limit=limit)

    @auth_only_api
    @json_response
    def post(self, app_name, kind):
        value = self.request.get('value')
        if value == '':
            self.response.set_status(400)
            return {'message': 'value is required'}

        try:
            app = model.Application.create(app_name)
            logging.info(app)
            data = app.addData(kind, float(value))
            return {'key': data.key.urlsafe()}

        except Exception as e:
            self.response.set_status(400)
            return {'message': e.message}

app = webapp2.WSGIApplication([
        webapp2.Route('/api/v1/<app_name>/info/', handler=AppInfoHandler, name='appInfoApi'),
        webapp2.Route('/api/v1/<app_name>/data/<kind>', handler=DataKindHandler, name='dataKindApi'),
        webapp2.Route('/api/v1/<app_name>/data/', handler=DataHandler, name='dataApi'),
], debug=True)