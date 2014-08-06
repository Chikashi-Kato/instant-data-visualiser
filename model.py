import uuid
import hashlib
import logging
import collections
import copy
import customdict
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
    email = ndb.StringProperty()
    user_id = ndb.StringProperty(required=True)
    shared_apps = ndb.KeyProperty(kind="Application", repeated=True)
    created = JsonConvertableDateTimeProperty(auto_now_add=True)

    @classmethod
    def create(cls, google_user, name=None):
        new_user = cls()
        new_user.user_id = google_user.user_id()
        new_user.email = google_user.email();
        if name != None:
            new_user.name = name
        else:
            new_user.name = google_user.nickname()

        new_user.put()

        return new_user

    @classmethod
    def getByGoogleUser(cls, google_user):
        user = cls.query(cls.user_id==google_user.user_id()).get()
        if user != None and user.email != google_user.email():
            user.email = google_user.email()
            user.put()

        return user

    @classmethod
    def getByEmail(cls, email):
        return cls.query(cls.email==email).get()

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
        return Application.getByUser(self, limit=limit)

    def getSharedApps(self, limit=20):
        return ndb.get_multi(self.shared_apps[0:limit])

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
    accessible_users = ndb.KeyProperty(kind="User", repeated=True)
    access_key = ndb.StringProperty()
    deleted = ndb.BooleanProperty(default=False)

    def getAccessKey(self):
        if self.access_key is None:
            self.access_key = getHashString(str(uuid.uuid4()))
            self.put()

        return self.access_key

    def allowAccess(self, user):
        if self.accessible_users == None:
            self.accessible_users = []

        if user.key not in self.accessible_users:
            self.accessible_users.append(user.key)
            self.put()

        if user.shared_apps == None:
            user.shared_apps = []

        if self.key not in user.shared_apps:
            user.shared_apps.append(self.key)
            user.put()

        return self

    def revokeAccess(self, user):
        self.accessible_users.remove(user.key)
        self.put()

        user.shared_apps.remove(self.key)
        user.put()

    def addData(self, kind, value, timestamp=None):
        if kind not in self.kinds:
            self.kinds.append(kind)
            self.put()

        return GraphData.create(self, kind, value, timestamp)

    def getOwner(self):
        return self.key.parent().get()

    def getInfo(self):
        info = {"key": self.key.urlsafe(),
                "owner": self.getOwner().key.urlsafe(),
                "name": self.name,
                "kinds": self.kinds}
        return info

    def getData(self, kind, limit=60):
        return GraphData.get(self, kind, limit)

    def getFormattedData(self, requestedKind=None, limit=60):
        if requestedKind == None:
            requestedKind = self.kinds

        results = {};
        results["cols"] = [{"id": "timestamp", "label": "Timestamp", "type": "datetime"}]
        blank_row = [];
        dataSet = collections.OrderedDict()
        for kind in self.kinds:
            if kind not in requestedKind:
                continue

            results["cols"].append({"id": kind, "label": kind, "type": "number"})
            blank_row.append({"v": None})
            dataSet[kind] = [p.to_dict() for p in self.getData(kind, limit)]

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

        results["rows"] = [{"c": value} for key, value in rows.items()]

        return results

    def isOwner(self, user):
        return (self.key.parent() == user.key)

    def isAccessible(self, user):
        return self.isOwner(user) or (user.key in self.accessible_users)

    def delete(self):
        # Delete data later
        self.deleted = True
        self.put()
        return self

    def deleteData(self):
        logging.info("deleteData")
        logging.info(self)

        GraphData.deleteAll(self)

        return

    @classmethod
    def create(cls, user, name):
        existing = cls.getByName(user, name)
        if existing != None:
            return existing

        app = cls(parent=user.key, name=name)
        app.put()

        return app

    @classmethod
    def getByUser(cls, user, deleted=False, limit=20):
        logging.info(deleted)
        return cls.query(cls.deleted==deleted, ancestor=user.key).fetch(limit=limit)

    @classmethod
    def getByName(cls, user, name, deleted=False):
        return cls.query(cls.name==name, cls.deleted==deleted, ancestor=user.key).get()

    @classmethod
    def getByAccessKey(cls, access_key, deleted=False):
        return cls.query(cls.access_key==access_key, cls.deleted==deleted).get()

    @classmethod
    def getDeletedApps(cls):
        return cls.query(cls.deleted==True).fetch()

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
        return cls.query(cls.kind==kind, ancestor=app.key).order(-cls.timestamp).fetch(limit=limit)

    @classmethod
    def deleteAll(cls, app):
        logging.info("deleteAll")
        while True:
            data = cls.query(ancestor=app.key).fetch(limit=1000, keys_only=True)
            if len(data) <= 0:
                break

            logging.info(data)
            ndb.delete_multi(data)

        return

