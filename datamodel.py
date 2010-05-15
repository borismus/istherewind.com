from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import memcache

# class WindCondition(db.Model):
#   datetime = db.DateTimeProperty(auto_now_add = False)
#   speed = db.FloatProperty()
#   direction = db.StringProperty()
#   created = db.DateTimeProperty(auto_now_add = True)
    
class Preference(db.Model):
  user = db.UserProperty()
  min_speed = db.IntegerProperty()
  should_notify = db.BooleanProperty()
  last_notified = db.DateTimeProperty(auto_now_add = True)
    
# assumes user is logged in
def get_or_create_prefs():
  user = users.get_current_user()
  prefs = db.GqlQuery('SELECT * FROM Preference WHERE user = :1', user).get()
  if not prefs:  
    prefs = Preference()
    prefs.user = user
    prefs.min_speed = 10
    prefs.max_speed = 20
    prefs.put()
  
  return prefs

def set_speed(data):
  memcache.add('speed', data, 3600)

def get_speed():
  return memcache.get('speed')