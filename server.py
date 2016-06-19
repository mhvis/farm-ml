#!/usr/bin/env python3
# vim: expandtab shiftwidth=4 softtabstop=4

import time
import os
import subprocess
from bottle import run, get, post, request, response, static_file

count = 1
root = '/home/maarten'
images = root + '/images'
models = root + '/models'
tf = root + '/tensorflow'
cmd_label = tf + '/bazel-bin/tensorflow/examples/label_image/label_image'
cmd_retrain = tf + '/bazel-bin/tensorflow/examples/image_retraining/retrain'

template = '''<!DOCTYPE html>
<html>
<body>
{}</body>
</html>'''

form_template = '''<form action="{}" method="post" enctype="multipart/form-data">
    {}<input type="file" name="media"><input type="submit" value="Upload">
</form>'''

form_multiple_template = '''<form action="{}" method="post" enctype="multipart/form-data">
    {}<input type="file" name="media" multiple><input type="submit" value="Upload">
</form>'''

def get_filename():
    global count
    name = time.strftime('%Y-%m-%d-%H-%M-%S') + '-' + str(count).zfill(4)
    count += 1
    return name

# Labeling

@post('/label/<imageset>')
def label(imageset):
    upload = request.files.get('media')
    name, ext = os.path.splitext(upload.filename)
    if ext.lower() not in ('.png','.jpg','.jpeg'):
        return 'File extension not allowed.'
    modeldir = models + '/' + imageset
    imagepath = modeldir + '/labeled/' + get_filename() + ext.lower()
    upload.save(imagepath)
    output = subprocess.check_output(
            [
                cmd_label,
                '--graph=' + modeldir + '/graph.pb',
                '--labels=' + modeldir + '/labels.txt',
                '--output_layer=final_result',
                '--image=' + imagepath
            ],
            stderr=subprocess.STDOUT).decode('utf-8')
    print(output)
    # Change below to be more general, accepting all categories
    if output.find(' accept ') < output.find(' reject' ):
        category = 'accept'
    else:
        category = 'reject'
    return category

# Adding

@post('/add/<imageset>/<category>')
def add(imageset, category):
    global count
    uploads = request.files.getall('media')
    count_ori = count
    for upload in uploads:
        name, ext = os.path.splitext(upload.filename)
        if ext.lower() not in ('.png','.jpg','.jpeg'):
            continue
        filename = get_filename() + ext.lower()
        savepath = images + '/' + imageset + '/' + category + '/' + filename
        upload.save(savepath)
    return 'Added {} images'.format(count - count_ori)

# Browsing

@get('/static/<filepath:path>')
def static(filepath):
    return static_file(filepath, root=images)

@get('/')
def index():
    return static_file('apidoc.html', root='/home/maarten/http')

@get('/browse')
def get_imagesets():
    imagesets = os.listdir(images)
    htmla = '<p><a href="/browse/{0}">/browse/{0}</a></p>\n'
    body = '<h1>Imagesets</h1>\n'
    body += ''.join([htmla.format(i) for i in imagesets])
    return template.format(body)

@get('/browse/<imageset>')
def get_imageset(imageset):
    categories = os.listdir(images + '/' + imageset)
    htmlimg = '<img src="/static/' + imageset + '/{}" width="100" height="100">\n'
    body = '<h1>Imageset \'' + imageset + '\'</h1>\n'
    body += form_template.format('/label/' + imageset, 'Label image: ')
    for category in categories:
        files = sorted(os.listdir(images + '/' + imageset + '/' + category))
        add = '/add/' + imageset + '/' + category
        body += '<h2>Category \'' + category + '\'</h2>\n'
        body += form_multiple_template.format(add, 'Add images: ')
        body += ''.join([htmlimg.format(category + '/' + f) for f in files])
    return template.format(body)

# Retraining

@get('/retrain/<imageset>')
def retrain(imageset):
    filename = get_filename()
    f = open(root + '/retrainlogs/' + filename, 'w')
    proc = subprocess.Popen(
            [
                cmd_retrain,
                '--image_dir=' + images + '/' + imageset,
                '--output_graph=' + models + '/' + imageset + '/graph.pb',
                '--output_labels=' + models + '/' + imageset + '/labels.txt',
                '--bottleneck_dir=' + models + '/' + imageset + '/bottleneck',
            ],
            stdin=None,
            stdout=f,
            stderr=subprocess.STDOUT)
    link = '<a href="/retrainlog/{0}">/retrainlog/{0}</a>'.format(filename)
    body = '<p>Retraining now, see log at {}</p>'.format(link)
    return template.format(body)

@get('/retrainlogs')
def retrainlogs():
    logs = sorted(os.listdir(root + '/retrainlogs'), reverse=True)
    htmla = '<p><a href="/retrainlog/{0}">/retrainlog/{0}</a></p>\n'
    body = '<h1>Retrain logs</h1>\n'
    body += ''.join([htmla.format(l) for l in logs])
    return template.format(body)

@get('/retrainlog/<log>')
def retrainlog(log):
    #response.headers['Content-Type'] = 'text/plain; charset=UTF-8'
    return static_file(log, root=root + '/retrainlogs')

if __name__ == '__main__':
    run(host='0.0.0.0', port=80)
