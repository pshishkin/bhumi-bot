import asyncio
import json
import os
import random
import string

import tornado.web
import tornado_http_auth
import settings
from mongo import MongoConnection
from video_mix_controller import VideoMixController

credentials = {'bhumi': settings.WEB_PASS}


class TestHandler(tornado.web.RequestHandler, tornado_http_auth.DigestAuthMixin):
    @tornado_http_auth.auth_required(realm='Protected', auth_func=credentials.get)
    def get(self):
        items = ["Item 1", "Item 2", "Item 3"]
        self.render("templates/template.html", title="My title", items=items)


class VideoMixHandler(tornado.web.RequestHandler, tornado_http_auth.DigestAuthMixin):
    @tornado_http_auth.auth_required(realm='Protected', auth_func=credentials.get)
    def get(self):
        self.render("templates/video_mix.html", title="My title")


class UploadHandler(tornado.web.RequestHandler, tornado_http_auth.DigestAuthMixin):
    @tornado_http_auth.auth_required(realm='Protected', auth_func=credentials.get)
    def post(self):
        file = self.request.files['file'][0]
        original_fname = file['filename']
        extension = os.path.splitext(original_fname)[1]
        fname = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))
        final_filename = fname + extension
        with open(os.path.join(UPLOAD, final_filename), 'wb') as output_file:
            output_file.write(file['body'])
        self.finish(json.dumps({'file_id': final_filename}))


def make_app():
    return tornado.web.Application([
        (r"/test/", TestHandler),
        (r"/video_mix/", VideoMixHandler),
        (r"/upload", UploadHandler),
    ])


async def main_tornado():
    app = make_app()
    app.listen(8432)
    await asyncio.Event().wait()


UPLOAD = os.path.join(settings.VIDEO_ROOT, 'upload')
DOWNLOAD = os.path.join(settings.VIDEO_ROOT, 'download')


def init_web():
    if not os.path.exists(settings.VIDEO_ROOT):
        os.mkdir(settings.VIDEO_ROOT)
    if not os.path.exists(UPLOAD):
        os.mkdir(UPLOAD)
    if not os.path.exists(DOWNLOAD):
        os.mkdir(DOWNLOAD)


async def async_init():
    MongoConnection.initialize()
    await VideoMixController.initialize()


def main_web():
    print('web')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_init())
    init_web()
    asyncio.run(main_tornado())
