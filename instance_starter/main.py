from oauth2client.client import GoogleCredentials
from googleapiclient.discovery import build
import webapp2
import urllib2
import threading
import logging

html_template = '''<!DOCTYPE html>
<html>
    <head>
        <title>Farm ML</title>
    </head>
    <body>
{}
    </body>
</html>'''

html_starting = '''
<p>
    The server is starting, please wait a minute (the page will refresh
    automatically).
</p>
<p>
    <strong>Background:</strong> due to server cost, the server stops
    automatically after 30 minutes.
</p>
<script>
window.setTimeout(function() {
    window.location.reload(true);
}, 10000);
</script>
'''

instance = {
        'project': 'plant-ml',
        'zone': 'europe-west1-c',
        'instance': 'large'
        }
timeout = 1800.0
timer = None

credentials = GoogleCredentials.get_application_default()
instances = build('compute', 'v1', credentials=credentials).instances()

def is_running():
    running = instances.get(**instance).execute()['status'] == 'RUNNING'
    logging.info('Retrieved running state: %s', running)
    return running

def is_accessible():
    if is_running():
        address = 'http://' + get_ip()
        try:
            urllib2.urlopen(address)
            logging.info('Instance is accessible at %s', address)
            return True
        except Exception as e:
            logging.info('Instance is not accessible: %s', e)
    return False

def get_ip():
    get = instances.get(**instance).execute()
    ip = str(get['networkInterfaces'][0]['accessConfigs'][0]['natIP'])
    logging.info('Retrieved IP: %s', ip)
    return ip

def start():
    logging.info('Starting instance')
    instances.start(**instance).execute()

def stop():
    logging.info('Stopping instance')
    instances.stop(**instance).execute()

def stop_after_timeout():
    logging.info('Scheduling stop after timeout')
    global timer
    if timer is not None and timer.is_alive():
        timer.cancel()
    timer = threading.Timer(timeout, stop)
    timer.daemon = True
    timer.start()
    logging.info('Scheduled stop after timeout')

class MainPage(webapp2.RequestHandler):
    def get(self):
        logging.info('Incoming request')
        if is_accessible():
            address = 'http://' + get_ip() + '/'
            logging.info('Redirecting to %s', address)
            self.redirect(address)
            stop_after_timeout()
            return
        self.response.write(html_template.format(html_starting))
        start()
        stop_after_timeout()

app = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)
