import webapp2
import model
import logging

class DeleteAppsHandler(webapp2.RequestHandler):
    def get(self):
        for app in model.Application.getDeletedApps():
            logging.info("Delete app")
            logging.info(app)

            app.deleteData()

            for user in app.getAccessibleUsers(limit=1000):
                user.shared_apps.remove(app.key)
                user.put()

            app.key.delete()

app = webapp2.WSGIApplication([
        webapp2.Route('/worker/delete-apps/', handler=DeleteAppsHandler, name='deleteApps'),
], debug=True)

