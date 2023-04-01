import asyncio
import hashlib
import json
import os
import random
import re
import string
import traceback

from concurrent.futures import ThreadPoolExecutor
from tornado.ioloop import IOLoop

import tornado.web
import tornado_http_auth
import settings
from mongo import MongoConnection
from video_mix_controller import VideoMixController
import functools

credentials = {settings.WEB_USERNAME: settings.WEB_PASS}


class AuthHandler(tornado.web.RequestHandler):
    def get(self, show_error=False):
        self.render("templates/auth_template.html", show_error=show_error)

    def post(self):
        username = self.get_argument("username")
        password = self.get_argument("password")

        if username in credentials and credentials[username] == password:
            self.set_secure_cookie("auth", tornado.escape.json_encode({"username": username}))
            self.redirect("/video_mixes/")
        else:
            self.get(show_error=True)


def auth_required(method):
    @functools.wraps(method)
    def wrapper(handler, *args, **kwargs):
        auth_data = tornado.escape.json_decode(handler.get_secure_cookie("auth")) if handler.get_secure_cookie(
            "auth") else None

        if auth_data and auth_data["username"] in credentials:
            return method(handler, *args, **kwargs)
        else:
            handler.redirect("/auth/")
            return None

    return wrapper


class TestHandler(tornado.web.RequestHandler, tornado_http_auth.DigestAuthMixin):
    @auth_required
    def get(self):
        items = ["Item 1", "Item 2", "Item 3"]
        self.render("templates/template.html", title="My title", items=items)


class VideoMixHandler(tornado.web.RequestHandler, tornado_http_auth.DigestAuthMixin):
    @auth_required
    async def get(self, video_mix_id=None):
        if video_mix_id:
            video_mix_id = video_mix_id.rstrip('/')
            video_mix = await VideoMixController().get_mix(video_mix_id)
            task_string = video_mix.task_string
            status_details = video_mix.status_details
        else:
            task_string = ""
            status_details = ""
        await self.render("templates/video_mix.html",
                          task_string=task_string,
                          status_details=status_details)


class UploadHandler(tornado.web.RequestHandler, tornado_http_auth.DigestAuthMixin):
    @auth_required
    def post(self):
        try:
            file = self.request.files['file'][0]
        except KeyError:
            raise tornado.web.HTTPError(status_code=400, reason="There's no file in the request")
        user_file_name = self.get_argument('fileName')
        original_fname = file['filename']
        base_name = os.path.splitext(original_fname)[0]
        extension = os.path.splitext(original_fname)[1]
        if not user_file_name:
            user_file_name = base_name
            # raise tornado.web.HTTPError(status_code=400, reason="Name must not be empty")
        if not re.search('^[a-zA-Z0-9_]+$', user_file_name):
            raise tornado.web.HTTPError(status_code=400, reason="Name can only contain english letters, numbers and underscores")
        # fname = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))
        # final_filename = fname + extension
        final_filename = user_file_name + extension
        if os.path.exists(os.path.join(UPLOAD, final_filename)):
            self.set_status(400)
            self.finish("File already uploaded, just use it. It's name is " + final_filename)
        with open(os.path.join(UPLOAD, final_filename), 'wb') as output_file:
            output_file.write(file['body'])
        self.finish(json.dumps({'file_id': final_filename}))


class GenerateHandler(tornado.web.RequestHandler, tornado_http_auth.DigestAuthMixin):
    executor = ThreadPoolExecutor(max_workers=4)

    @auth_required
    async def post(self):
        try:
            mix_request = self.get_argument('generateTask')
        except KeyError:
            raise tornado.web.HTTPError(status_code=400, reason="There's no request in the request")
        file_names = mix_request.strip().split()
        if len(file_names) < 2:
            raise tornado.web.HTTPError(status_code=400, reason="There must be at least 2 files")
        # extension = os.path.splitext(file_names[0])[1]
        file_pathes = [os.path.join(UPLOAD, file_name) for file_name in file_names]
        # generate_video_mix(file_pathes, output_path)

        # Start generate_video_mix in a background thread
        # thread = threading.Thread(target=wrap_generate_video_mix, args=(mix_request, file_pathes, output_path))
        # thread.start()
        self.write('''
        Your request has been received.
        Checkout out <a href="/video_mixes/">video mixes</a> url to see the result
        ''')
        IOLoop.current().add_callback(execute_and_save, mix_request, file_pathes)


class NoVideoException(Exception):
    pass


class VideoMixListHandler(tornado.web.RequestHandler, tornado_http_auth.DigestAuthMixin):
    @auth_required
    async def get(self):
        video_mixes = await video_mix_controller.get_all_mixes()
        print(video_mixes[0])
        await self.render("templates/video_mix_list.html", title="Video Mix List", video_mixes=video_mixes)


async def execute_and_save(mix_request, file_pathes):
    print('execute_and_save')
    mix_id = await video_mix_controller.add_mix(mix_request)
    output_name = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(6)) + '.mp4'
    output_path = os.path.join(DOWNLOAD, output_name)
    result = await IOLoop.current().run_in_executor(GenerateHandler.executor, wrap_generate_video_mix, file_pathes, output_path)
    if result is None:
        await video_mix_controller.mark_mix_as_succeed(mix_id, output_name)
    else:
        await video_mix_controller.mark_mix_as_failed(mix_id, str(result))
    # await save_result_to_mongo(result)


def wrap_generate_video_mix(video_files, output_file):
    try:
        print("wrap_generate_video_mix")
        for file in video_files:
            if not os.path.exists(file):
                raise NoVideoException(f'File {os.path.split(file)[1]} does not exist')
        generate_video_mix(video_files, output_file)
    except Exception as e:
        print(f'wrap_generate_video_mix exception: {str(e)}')
        traceback.print_exc()
        return e
    else:
        print('ok fine')


from moviepy.editor import (
    concatenate_videoclips, VideoFileClip, AudioFileClip, concatenate_audioclips, ColorClip, CompositeVideoClip
)
import os

def generate_video_mix(video_files, output_file):
    video_clips = []
    audio_clips = []
    first_video = VideoFileClip(video_files[0])
    width, height = first_video.size

    for video_file in video_files:
        if os.path.exists(video_file):
            clip = VideoFileClip(video_file)

            # Resize video maintaining aspect ratio
            if clip.aspect_ratio >= first_video.aspect_ratio:
                clip_resized = clip.resize(width=None, height=height)
            else:
                clip_resized = clip.resize(width=width, height=None)

            # Pad the video
            pad_left = int((width - clip_resized.w) / 2)
            pad_top = int((height - clip_resized.h) / 2)

            background = ColorClip((width, height), color=(0, 0, 0), duration=clip_resized.duration)
            clip_padded = CompositeVideoClip([background, clip_resized.set_position(("center", "center"))])

            video_clips.append(clip_padded)
            audio_clips.append(AudioFileClip(video_file))
        else:
            print(f"File {video_file} not found. Skipping...")

    # Concatenate video and audio clips separately
    final_video = concatenate_videoclips(video_clips)
    final_audio = concatenate_audioclips(audio_clips)

    # Set the final audio to the video
    final_clip = final_video.set_audio(final_audio)

    # Write the output file
    final_clip.write_videofile(output_file, codec='libx264', audio_codec='aac')


class DownloadHandler(tornado.web.StaticFileHandler):
    async def get(self, filename, include_body=True):
        await super().get(filename, include_body)


def make_app():

    return tornado.web.Application([
        (r"/test/", TestHandler),
        (r"/auth/", AuthHandler),
        (r"/video_mix/([a-zA-Z0-9]*/?)", VideoMixHandler),
        (r"/video_mix_download/(.*)", DownloadHandler, {"path": DOWNLOAD}),
        (r"/video_mixes/", VideoMixListHandler),
        (r"/upload", UploadHandler),
        (r"/generate", GenerateHandler),
    ])


async def main_tornado():
    app = make_app()
    app.listen(8432)
    app.settings["cookie_secret"] = hashlib.sha256(settings.COOKIE_SECRET.encode()).hexdigest()
    await asyncio.Event().wait()


UPLOAD = os.path.join(settings.VIDEO_ROOT, 'upload')
DOWNLOAD = os.path.join(settings.VIDEO_ROOT, 'download')
video_mix_controller = VideoMixController()


def init_web():
    # client = AsyncIOMotorClient()
    # client.get_io_loop = asyncio.get_event_loop
    # engine = AIOEngine(motor_client=client)

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
    init_web()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_init())
    asyncio.run(main_tornado())
