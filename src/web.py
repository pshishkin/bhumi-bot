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

from crypto import Crypto
import settings
from drop_user_controller import DropUserController
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

def get_user_allowance(user_id: str) -> (int, str):
    found_in_groups = []
    # look through all json files in folder and create a list of files where user_id is present
    for file in os.listdir(settings.SNAPSHOTS_DIR):
        if file.endswith(".json"):
            with open(os.path.join(settings.SNAPSHOTS_DIR, file), 'r') as f:
                data = json.load(f)
                if user_id in data['users']:
                    found_in_groups.append(data['name'])

    details = 'ни в каких'
    allowance_user = settings.BHUMI_DROP_BASE

    if found_in_groups:
        details = ', '.join(found_in_groups)
        allowance_user = settings.BHUMI_DROP_BASE * (1 + len(found_in_groups))

    return allowance_user, details


class AirdropAmountHandler(tornado.web.RequestHandler):
    async def get(self):
        user_id = self.get_argument('user_id')
        if not user_id:
            raise tornado.web.HTTPError(status_code=400, reason="No user_id provided")

        allowance_user, details = get_user_allowance(user_id)

        user_obj = await drop_user_controller.get_user(user_id)
        claimed_user = user_obj.claimed
        claimed_total = await drop_user_controller.get_total_claimed()

        await self.finish(json.dumps({'allowance_user': allowance_user, 'details': details, 'claimed_user': claimed_user, 'claimed_total': claimed_total}))


class AirdropDropHandler(tornado.web.RequestHandler):
    async def get(self):
        user_id = self.get_argument('user_id')
        if not user_id:
            raise tornado.web.HTTPError(status_code=400, reason="No user_id provided")
        wallet = self.get_argument('wallet')
        if not wallet:
            raise tornado.web.HTTPError(status_code=400, reason="No wallet provided")
        ref = self.get_argument('ref')
        if not ref:
            ref = ''

        allowance_user, details = get_user_allowance(user_id)

        user_obj = await drop_user_controller.get_user(user_id)
        claimed_user = user_obj.claimed

        if claimed_user >= allowance_user:
            await self.finish(json.dumps({'drop_details': 'У тебя нет BHUMI которые можно было бы получить', 'dropped_amount': 0}))

        drop_amount = allowance_user - claimed_user

        # drop should happen here
        hash = await crypto.transfer_drop(wallet, drop_amount, settings.SOL_DROP_AMOUNT)
        await drop_user_controller.add_claim(user_id, drop_amount, wallet, ref)

        await self.finish(json.dumps({'drop_details': f'Отправил {drop_amount} BHUMI по адресу {wallet}\n\n Ссылка на транзакцию: https://solscan.io/tx/{hash}', 'dropped_amount': drop_amount}))


from io import BytesIO
import qrcode

class QRCodeHandler(tornado.web.RequestHandler):
    async def get(self):
        data = self.get_argument('data', 'Hello, Tornado!')
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = BytesIO()
        img.save(img_buffer, "PNG")
        img_buffer.seek(0)
        self.set_header("Content-Type", "image/png")
        self.set_header("Content-Length", img_buffer.getbuffer().nbytes)
        self.write(img_buffer.getvalue())

def make_app():

    return tornado.web.Application([
        (r"/test/", TestHandler),
        (r"/auth/", AuthHandler),
        (r"/video_mix/([a-zA-Z0-9]*/?)", VideoMixHandler),
        (r"/video_mix_download/(.*)", DownloadHandler, {"path": DOWNLOAD}),
        (r"/video_mixes/", VideoMixListHandler),
        (r"/upload", UploadHandler),
        (r"/generate", GenerateHandler),
        (r"/airdrop/amount", AirdropAmountHandler),
        (r"/airdrop/drop", AirdropDropHandler),
        (r"/qrcode", QRCodeHandler),
    ])


async def main_tornado():
    app = make_app()
    app.listen(8432)
    app.settings["cookie_secret"] = hashlib.sha256(settings.COOKIE_SECRET.encode()).hexdigest()
    await asyncio.Event().wait()


UPLOAD = os.path.join(settings.VIDEO_ROOT, 'upload')
DOWNLOAD = os.path.join(settings.VIDEO_ROOT, 'download')
video_mix_controller = VideoMixController()
drop_user_controller = DropUserController()
crypto = Crypto()

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
    await DropUserController.initialize()


def main_web():
    init_web()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_init())
    asyncio.run(main_tornado())
