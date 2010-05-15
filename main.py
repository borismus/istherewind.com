#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import wsgiref.handlers
import os
from datetime import datetime, timedelta

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch, users
import logging

import datamodel

class MainHandler(webapp.RequestHandler):

  def get(self):
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url(self.request.uri))
      return
    
    self.render_main_page()
  
  def post(self):
    prefs = datamodel.get_or_create_prefs()
    prefs.min_speed = int(self.request.get('min_speed'))
    prefs.put()

    self.render_main_page(updated=True)
      
  def render_main_page(self, updated=False):
    user = users.get_current_user()
    prefs = datamodel.get_or_create_prefs()
    average_speed = datamodel.get_speed()
    
    template_values = {
      'windy': average_speed > prefs.min_speed,
      'average_speed': average_speed,
      'min_speed': prefs.min_speed,
      'updated': updated,
      'user': user.nickname(),
      'logout_url': users.create_logout_url('/')
    }

    path = os.path.join(os.path.dirname(__file__), 'welcome.html')
    self.response.out.write(template.render(path, template_values))

class UpdateHandler(webapp.RequestHandler):

  def get(self):
    url = "http://www.jsca.bc.ca/main/download.txt"
    headers = {
      'Cache-Control': 'no-store, no-cache, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': repr(datetime.now())
      }
    # Force skipped caching with headers
    result = urlfetch.fetch(url, headers=headers)
    if result.status_code == 200:
      self.parse(result.content)
      self.is_there_wind()
    else:
      self.error(500)

  def parse(self, content):
    total_speed = 0
    lines = content.split('\n')
    # ignore the first two lines and the last line
    lines = lines[2:-1]
    for line in lines:
      words = line.split('\t')
      speed = float(words[11])
      total_speed += speed

    data_count = len(lines)
    average_speed = total_speed / data_count
    datamodel.set_speed(average_speed)
    
    logging.info('Fetched data from %d points.' % data_count)

  def is_there_wind(self):
    average_speed = datamodel.get_speed()
    prefs = db.GqlQuery('SELECT * FROM Preference WHERE min_speed < :1', int(average_speed))

    now = datetime.now()
    time_limit = now - timedelta(hours=4)

    for pref in prefs:
      if pref.last_notified > time_limit:
        # don't notify if we've already sent notification recently
        continue
      self.send_notification(pref, average_speed)
      pref.last_notified = now
      pref.put()

  def send_notification(self, pref, average_speed):
    place = 'Jericho Beach'
    name = pref.user.nickname()
    email = pref.user.email()
    from google.appengine.api import mail
    mail.send_mail(sender="noreply@istherewind.com",
                  to="%s <%s>" % (name, email),
                  subject="The wind is %s knots at %s..." %(average_speed, place),
                  body="""Dear %s:

To change your notification preferences, please visit http://istherewind.com.

Stay safe out there!
-The istherewind.com Team""" % (name) )

    logging.info('Sent wind notification email to %s <%s>' %(name, email))


def main():
  application = webapp.WSGIApplication([('/', MainHandler),
                                        ('/update', UpdateHandler)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
