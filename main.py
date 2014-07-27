#!/usr/bin/env python
import os
import copy
import webapp2
import model
import logging
import json
import datetime
import jinja2
import collections

TEMPLATE_PATH = os.path.dirname(__file__) + '/views'
jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_PATH, encoding='utf8'),
    autoescape=True)

class CustomOrderedDefaultdict(collections.OrderedDict):
    def __init__(self, *args, **kwargs):
        if not args:
            self.default_factory = None
        else:
            if not (args[0] is None or callable(args[0])):
                raise TypeError('first argument must be callable or None')
            self.default_factory = args[0]
            args = args[1:]
        super(CustomOrderedDefaultdict, self).__init__(*args, **kwargs)

    def __missing__ (self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = default = self.default_factory(key)
        return default

    def __reduce__(self):  # optional, for pickle support
        args = (self.default_factory,) if self.default_factory else ()
        return self.__class__, args, None, None, self.iteritems()

class CustomDefaultDict(dict):
    def __init__(self, factory):
        self.factory = factory

    def __missing__(self, key):
        self[key] = self.factory(key)
        return self[key]

def json_response(method):
    def wrapper(self, *args, **kwargs):
        self.response.headers['Content-Type'] = 'application/json'
        data = method(self, *args, **kwargs)
        self.response.write(json.dumps(data))

    return wrapper

class GraphHandler(webapp2.RequestHandler):
    def get(self, app_name):
        template = jinja_env.get_template("graph.html")
        template_values = {}
        template_values["app_name"] = app_name
        self.response.out.write(template.render(template_values))

class DataHandler(webapp2.RequestHandler):
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

        rows = CustomOrderedDefaultdict(row_factory)

        col_position = 0
        for kind, values in dataSet.items():
            col_position += 1
            for v in values:
                rows[v["timestamp"]][col_position]["v"] = v["value"]
                logging.info(rows)

        results["rows"] = [{"c": value} for key, value in rows.items()]

        return results

    @json_response
    def post(self, app_name):
        data = self.request.get('data')
        data = json.loads(data)

        app = model.Application.create(app_name)

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
    @json_response
    def get(self, app_name, kind):
        limit = self.request.get('limit', 60)

        app = model.Application.getByName(app_name)
        if app == None:
            self.response.set_status(404)
            return {'message': 'application not found: ' + app_name}

        return [p.to_dict() for p in app.getData(kind, limit)]

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
        webapp2.Route('/<app_name>/graph/', handler=GraphHandler, name='graph'),
        webapp2.Route('/api/v1/<app_name>/data/<kind>', handler=DataKindHandler, name='dataKindApi'),
        webapp2.Route('/api/v1/<app_name>/data/', handler=DataHandler, name='dataApi'),
], debug=True)
