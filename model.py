import uuid
import hashlib
from google.appengine.ext import ndb

# generate hashed string
def getHashString(target):
    salt = str(uuid.uuid4().get_hex()[0:6])
    return hashlib.sha256(target + salt).hexdigest()

class JsonConvertableDateTimeProperty(ndb.DateTimeProperty):
    def  _get_for_dict(self, entity):
        return self._get_value(entity).strftime('%Y-%m-%dT%H:%M:%S')

class User(ndb.Model):
    name = ndb.StringProperty(default="Anonymous")
    user_obj = ndb.UserProperty(required=True)
    created = JsonConvertableDateTimeProperty(auto_now_add=True)

    @classmethod
    def create(cls, user, name=None):
        new_user = cls()
        new_user.user_obj = user
        if name != None:
            new_user.name = name

        new_user.put()

        return new_user

    @classmethod
    def getByGoogleUser(cls, user):
        return cls.query(cls.user_obj==user).get()

    @classmethod
    def getByToken(cls, token_str):
        token = AuthToken.getByToken(token_str)
        if token is None:
            return None

        return token.getOwner()

    def getToken(self):
        current_token = AuthToken.getByUser(self)
        if current_token != None:
            return current_token

        new_token = AuthToken.create(self)
        return new_token

    def getMyApps(self, limit=20):
        return Application.getByUser(self, limit)

class AuthToken(ndb.Model):
    token = ndb.StringProperty(required=True)
    enabled = ndb.BooleanProperty(default=True)
    created = JsonConvertableDateTimeProperty(auto_now_add=True)

    @classmethod
    def create(cls, user):
        new_token = cls(parent=user.key)
        new_token.token = getHashString(str(uuid.uuid4()))
        new_token.put()
        return new_token

    @classmethod
    def getByUser(cls, user):
        return cls.query(cls.enabled==True, ancestor=user.key).get()

    @classmethod
    def getByToken(cls, token_str):
        return cls.query(cls.token==token_str, cls.enabled==True).get()

    def getOwner(self):
        return self.key.parent().get()

    def disable(self):
        self.enabled = False
        self.put()

        return self

    def __str__(self):
        return self.token

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
    def create(cls, user, name):
        existing = cls.getByName(user, name)
        if existing != None:
            return existing

        app = cls(parent=user.key, name=name)
        app.put()

        return app

    @classmethod
    def getByUser(cls, user, limit=20):
        return cls.query(ancestor=user.key).fetch(limit=limit)

    @classmethod
    def getByName(cls, user, name):
        return cls.query(cls.name==name, ancestor=user.key).get()

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
