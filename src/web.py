import asyncio
import json
import os
import random
import re
import string
import ffmpeg

import tornado.web
import tornado_http_auth
import settings
from mongo import MongoConnection
from video_mix_controller import VideoMixController

credentials = {settings.WEB_USERNAME: settings.WEB_PASS}


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
        try:
            file = self.request.files['file'][0]
        except KeyError:
            raise tornado.web.HTTPError(status_code=400, reason="There's no file in the request")
        user_file_name = self.get_argument('fileName')
        if not user_file_name:
            raise tornado.web.HTTPError(status_code=400, reason="Name must not be empty")
        if not re.search('^[a-zA-Z0-9_]+$', user_file_name):
            raise tornado.web.HTTPError(status_code=400, reason="Name can only contain english letters, numbers and underscores")
        original_fname = file['filename']
        extension = os.path.splitext(original_fname)[1]
        # fname = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))
        # final_filename = fname + extension
        final_filename = user_file_name + extension
        if os.path.exists(os.path.join(UPLOAD, final_filename)):
            self.set_status(400)
            self.finish("File already exists")
        with open(os.path.join(UPLOAD, final_filename), 'wb') as output_file:
            output_file.write(file['body'])
        self.finish(json.dumps({'file_id': final_filename}))


class GenerateHandler(tornado.web.RequestHandler, tornado_http_auth.DigestAuthMixin):
    @tornado_http_auth.auth_required(realm='Protected', auth_func=credentials.get)
    def post(self):
        try:
            mix_request = self.get_argument('generateTask')
        except KeyError:
            raise tornado.web.HTTPError(status_code=400, reason="There's no request in the request")
        file_names = mix_request.strip().split()
        if len(file_names) < 2:
            raise tornado.web.HTTPError(status_code=400, reason="There must be at least 2 files")
        # extension = os.path.splitext(file_names[0])[1]
        file_pathes = [os.path.join(UPLOAD, file_name) for file_name in file_names]
        output_name = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(6)) + '.mp4'
        output_path = os.path.join(DOWNLOAD, output_name)
        generate_video_mix(file_pathes, output_path)
        self.finish(f"OK {file_names}, {output_path}")


class NoVideoException(Exception):
    pass


def generate_video_mix(video_files, output_file):
    # Create a list to hold the input streams
    video_streams = []
    audio_streams = []

    # Get the size of the first video
    probe = ffmpeg.probe(video_files[0])
    video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    width = video_info['width']
    height = video_info['height']

    # Iterate through the video files and add their streams to the list
    for video_file in video_files:
        if os.path.exists(video_file):
            video_stream = ffmpeg.input(video_file)

            # Resize the video using padding to maintain the aspect ratio
            video_resized = (
                video_stream.video
                .filter('scale', width, f"'min({height}, iw*{height}/ih)'")
                .filter('pad', width, height, f'({width}-iw)/2', f'({height}-ih)/2')
                .filter('setpts', 'PTS-STARTPTS')
            )

            # Trim the audio stream and set the PTS
            audio_trimmed = video_stream.audio.filter('atrim').filter('asetpts', 'PTS-STARTPTS')

            # Add the resized video and trimmed audio streams to the list
            video_streams.append(video_resized)
            audio_streams.append(audio_trimmed)
        else:
            raise NoVideoException(f"File {video_file} does not exist")

    # Concatenate the video and audio streams separately
    concatenated_video_node = ffmpeg.concat(*(stream for stream in video_streams), v=1, a=0)
    concatenated_audio_node = ffmpeg.concat(*(stream for stream in audio_streams), v=0, a=1)

    # Define the output stream and format
    output_stream = ffmpeg.output(concatenated_video_node, concatenated_audio_node, output_file, format='mp4')

    # Run the ffmpeg command to concatenate the videos
    ffmpeg.run(output_stream)


def make_app():
    return tornado.web.Application([
        (r"/test/", TestHandler),
        (r"/video_mix/", VideoMixHandler),
        (r"/upload", UploadHandler),
        (r"/generate", GenerateHandler),
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
