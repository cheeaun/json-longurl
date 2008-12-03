#!/usr/bin/env python

import re
import cgi
import time
import logging
import datetime
import wsgiref.handlers
from rfc822 import formatdate
from django.utils import simplejson

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.api import urlfetch

class MainHandler(webapp.RequestHandler):
  def get(self):
    url = cgi.escape(self.request.get('url'))
    callback = cgi.escape(self.request.get('callback'))
    obj = {}
    longurl = None

#    for debugging
#    memcache.flush_all()
    
    if url:
      json = memcache.get(url)
      
      if json is None:
        logging.info('The url is NOT in memcache')
        longurl = expand(url)
        
        obj['url'] = longurl
        obj['redirected'] = longurl != url
        
        json = simplejson.dumps(obj, sort_keys=True, indent=4)
        
        logging.debug('Adding json output to memcache')
        memcache.add(url, json, 3600) # 1 hour
        
      else:
        logging.info('The url is in memcache')
        
      if callback:
        logging.info('Adding callback to JSON')
        exp = re.compile('^[A-Za-z_$][A-Za-z0-9_$]*?$')
        match = exp.match(callback)
        if match: json = callback + '(' + json + ')'

      d = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
      expires = formatdate(time.mktime(d.timetuple()))
      self.response.headers['Expires'] = expires
      
      self.response.headers['Content-Type'] = 'application/javascript'
      self.response.out.write(json)
      
    else:
      self.response.out.write("""
      <!DOCTYPE html>
      <title>json-longurl</title>
      <h1>json-longurl</h1>
      <p>JSON (and JSON-P) API for expanding a shortened URL or getting the destination URL of a redirection URL.
      <ul>
          <li><a href="/?url=http://tinyurl.com/161">/?url=http://tinyurl.com/161</a>
          <li><a href="/?url=http://is.gd/ckJ&amp;callback=foo">/?url=http://is.gd/ckJ&amp;callback=foo</a>
          <li><a href="/?url=http://google.com/">/?url=http://google.com/</a>
          <li><a href="/?url=http://www.google.com/">/?url=http://www.google.com/</a>
      </ul>
      <p>Inspired by <a href="http://longurl.org/">LongURL</a>. You may also like <a href="http://json-pagetitle.appspot.com/">json-pagetitle</a>.</p>
      """)

def expand(url):
  try:
    result = urlfetch.fetch(url, method='HEAD', follow_redirects=False)
    
    if result.status_code == 405:
      logging.debug('The url returns a 405, no HEAD request')
      result = urlfetch.fetch(url, follow_redirects=False)
    
    if result.status_code == 301:
      logging.info('The url redirects')
      longurl = result.headers.get('location')
      return expand(longurl) # recursive expand of the URL
    else:
      logging.info('The url does NOT redirect')
      return url
  except urlfetch.Error:
    pass

def main():
  application = webapp.WSGIApplication([('/', MainHandler)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
