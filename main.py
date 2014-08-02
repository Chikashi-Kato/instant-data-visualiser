#!/usr/bin/env python
import os
import webapp2
import model
import logging
import jinja2
from google.appengine.api import users
from google.appengine.api import channel
from google.appengine.api import memcache

TEMPLATE_PATH = os.path.dirname(__file__) + '/views'
jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_PATH, encoding='utf8'),
    autoescape=True)

def auth_required(method):
    def wrapper(self, *args, **kwargs):
        # Checks for active Google account session
        google_user = users.get_current_user()

        if google_user:
            user = model.User.getByGoogleUser(google_user)
            if user == None:
                user = model.User.create(google_user, google_user.nickname())

            self.user = user
            method(self, *args, **kwargs)

        else:
            self.redirect(users.create_login_url(self.request.uri))

    return wrapper

class GraphHandler(webapp2.RequestHandler):
    @auth_required
    def get(self, access_key):
        app = model.Application.getByAccessKey(access_key)
        if app is None:
            self.response.set_status(404)
            return

        if not app.isAccessible(self.user):
            self.response.set_status(403)
            return

        template = jinja_env.get_template("graph.html")
        template_values = {}
        template_values["isOwner"] = app.isOwner(self.user)
        template_values["access_key"] = access_key
        template_values["token"] = self.user.getToken()
        self.response.out.write(template.render(template_values))

class ShowMyAppsHandler(webapp2.RequestHandler):
    @auth_required
    def get(self):
        template = jinja_env.get_template("apps.html")
        template_values = {}
        template_values["apps"] = self.user.getMyApps()
        template_values["sharedApps"] = self.user.getSharedApps()
        template_values["token"] = self.user.getToken()
        self.response.out.write(template.render(template_values))

class ChannelConnectedHandler(webapp2.RequestHandler):
    def post(self):
        client_id = self.request.get('from')
        logging.info(client_id + " is connected.")

        channel_info = memcache.get(client_id)
        if channel_info is None:
            logging.info("client_id is not found")
            return

        logging.info("channel_info here")
        logging.info(channel_info)

        channel_tokens = memcache.get(channel_info["access_key"])
        if channel_tokens is None:
            channel_tokens = []

        channel_tokens.append(channel_info["channel_token"])
        logging.info(channel_info["access_key"])
        logging.info(channel_info["channel_token"])
        memcache.set(channel_info["access_key"], channel_tokens)

class ChannelDisconnectedHandler(webapp2.RequestHandler):
    def post(self):
        client_id = self.request.get('from')
        logging.info(client_id + " is disconnected.")

        channel_info = memcache.get(client_id)
        if channel_info is None:
            logging.info("client_id is not found")
            return

        channel_tokens = memcache.get(channel_info["access_key"])
        if channel_tokens is None:
            logging.info("access_key is not found")
            return

        if channel_info["channel_token"] in channel_tokens:
            channel_tokens.remove(channel_info["channel_token"])
            memcache.set(channel_info["access_key"], channel_tokens)

        #memcache.delete(client_id)

app = webapp2.WSGIApplication([
        webapp2.Route('/<access_key>/graph/', handler=GraphHandler, name='graph'),
        webapp2.Route('/_ah/channel/connected/', handler=ChannelConnectedHandler, name='channelConnected'),
        webapp2.Route('/_ah/channel/disconnected/', handler=ChannelDisconnectedHandler, name='channelDisconnected'),
        webapp2.Route('/', handler=ShowMyAppsHandler, name='showMyApps'),
], debug=True)
