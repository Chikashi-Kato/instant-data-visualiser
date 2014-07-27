from google.appengine.ext import ndb

class JsonConvertableDateTimeProperty(ndb.DateTimeProperty):
    def  _get_for_dict(self, entity):
        return self._get_value(entity).strftime('%Y-%m-%dT%H:%M:%S')

class Application(ndb.Model):
    name = ndb.StringProperty()
    kinds = ndb.StringProperty(repeated=True)

    def addData(self, kind, value, timestamp=None):
        if kind not in self.kinds:
            self.kinds.append(kind)
            self.put()

        return GraphData.create(self, kind, value, timestamp)

    def getData(self, kind, limit=60):
        return GraphData.get(self, kind, limit)

    @classmethod
    def create(cls, name):
        existing = cls.getByName(name)
        if existing != None:
            return existing

        app = cls(name=name)
        app.put()

        return app

    @classmethod
    def getByName(cls, name):
        return cls.query(cls.name==name).get()

class GraphData(ndb.Model):
    kind = ndb.StringProperty()
    value = ndb.FloatProperty()
    timestamp = JsonConvertableDateTimeProperty(auto_now=True)

    @classmethod
    def create(cls, app, kind, value, timestamp=None):
        data = cls(parent=app.key)
        data.kind = kind
        data.value = value
        if timestamp is not None:
            data.timestamp = timestamp
        data.put()

        return data

    @classmethod
    def get(cls, app, kind, limit=60):
        return cls.query(cls.kind==kind).order(-cls.timestamp).fetch(limit)
