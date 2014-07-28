#!/usr/bin/env python
import os
import copy
import webapp2
import model
import customdict
import logging
import json
import datetime
import jinja2
import collections
from google.appengine.api import users

TEMPLATE_PATH = os.path.dirname(__file__) + '/views'
jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_PATH, encoding='utf8'),
    autoescape=True)

def auth_required(method):
    def wrapper(self, *args, **kwargs):
        # Checks for active Google account session
        google_user = users.get_current_user()
        user = model.User.getByGoogleUser(google_user)
        if user == None:
            user = model.User.create(google_user, google_user.nickname())

        if user:
            self.user = user
            method(self, *args, **kwargs)
        else:
            self.redirect(users.create_login_url(self.request.uri))

    return wrapper

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

class GraphHandler(webapp2.RequestHandler):
    @auth_required
    def get(self, app_name):
        template = jinja_env.get_template("graph.html")
        template_values = {}
        template_values["app_name"] = app_name
        template_values["token"] = self.user.getToken()
        self.response.out.write(template.render(template_values))

class DataHandler(webapp2.RequestHandler):
    @auth_only_api
    @json_response
    def get(self, app_name):
        limit = self.request.get('limit', 60)

        app = model.Application.getByName(app_name)
        if app == None:
            self.response.set_status(404)
            return {'message': 'application not found: ' + app_name}

        results = {};
        results["cols"] = [{"id": "timestamp", "label": "Timestamp", "type": "datetime"}]
        blank_row = [];
        dataSet = collections.OrderedDict()
        for kind in app.kinds:
            results["cols"].append({"id": kind, "label": kind, "type": "number"})
            blank_row.append({"v": None})
            dataSet[kind] = [p.to_dict() for p in app.getData(kind, limit)]

        def row_factory(key):
            r = copy.deepcopy(blank_row)
            r.insert(0, {"v": key})
            logging.info("New row:  %s " % r)
            return r

        rows = customdict.CustomOrderedDefaultdict(row_factory)

        col_position = 0
        for kind, values in dataSet.items():
            col_position += 1
            for v in values:
                rows[v["timestamp"]][col_position]["v"] = v["value"]
                logging.info(rows)

        results["rows"] = [{"c": value} for key, value in rows.items()]

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

        app = model.Application.getByName(app_name)
        if app == None:
            self.response.set_status(404)
            return {'message': 'application not found: ' + app_name}

        return [p.to_dict() for p in app.getData(kind, limit)]

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

class ShowMyAppsHandler(webapp2.RequestHandler):
    @auth_required
    def get(self):
        token = self.user.getToken()
        apps = self.user.getMyApps()

        template = jinja_env.get_template("apps.html")
        template_values = {}
        template_values["apps"] = apps
        template_values["token"] = self.user.getToken()
        self.response.out.write(template.render(template_values))

app = webapp2.WSGIApplication([
        webapp2.Route('/<app_name>/graph/', handler=GraphHandler, name='graph'),
        webapp2.Route('/api/v1/<app_name>/data/<kind>', handler=DataKindHandler, name='dataKindApi'),
        webapp2.Route('/api/v1/<app_name>/data/', handler=DataHandler, name='dataApi'),
        webapp2.Route('/', handler=ShowMyAppsHandler, name='showMyApps'),
], debug=True)
