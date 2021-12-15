# -*- coding: utf-8 -*-

__all__ = ()

import hashlib
import os
import time
import pycountry
import timeago

from cmyui.logging import Ansi
from cmyui.logging import log
from functools import wraps
from PIL import Image
from pathlib import Path
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand
from cryptography.hazmat.backends import default_backend as backend
from quart import Blueprint
from quart import redirect
from quart import render_template
from quart import request
from quart import session
from quart import send_file
from datetime import datetime

from constants import regexes
from objects import glob
from objects import utils
from objects.privileges import Privileges
from objects.utils import flash
from objects.utils import flash_with_customizations

VALID_MODES = frozenset({'std', 'taiko', 'catch', 'mania'})
VALID_MODS = frozenset({'vn', 'rx', 'ap'})

frontend = Blueprint('frontend', __name__)

def login_required(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not session:
            return await flash('error', 'You must be logged in to access that page.', 'login')
        return await func(*args, **kwargs)
    return wrapper

@frontend.route('/home')
@frontend.route('/')
async def home():
    vn = await glob.db.fetchrow('SELECT pp, users.name, time FROM scores LEFT JOIN users ON scores.uid = users.id LEFT JOIN maps ON scores.md5 = maps.md5 WHERE users.priv & 2 AND NOT users.priv & 1024 AND maps.status = 2 AND scores.status = 2 AND scores.mode = 0 ORDER BY pp DESC LIMIT 1')
    rx = await glob.db.fetchrow('SELECT pp, users.name, time FROM scores_rx LEFT JOIN users ON scores_rx.uid = users.id LEFT JOIN maps ON scores_rx.md5 = maps.md5 WHERE users.priv & 2 AND NOT users.priv & 1024 AND maps.status = 2 AND scores_rx.status = 2 AND scores_rx.mode = 0 ORDER BY pp DESC LIMIT 1')
    ap = await glob.db.fetchrow('SELECT pp, users.name, time FROM scores_ap LEFT JOIN users ON scores_ap.uid = users.id LEFT JOIN maps ON scores_ap.md5 = maps.md5 WHERE users.priv & 2 AND NOT users.priv & 1024 AND maps.status = 2 AND scores_ap.status = 2 AND scores_ap.mode = 0 ORDER BY pp DESC LIMIT 1')
    try:
        return await render_template('home.html', vnpp=round(vn['pp']), vndate=timeago.format(datetime.fromtimestamp(vn['time'])), rxdate=timeago.format(datetime.fromtimestamp(rx['time'])), apdate=timeago.format(datetime.fromtimestamp(ap['time'])), vnuser=vn['name'], rxpp=round(rx['pp']), rxuser=rx['name'], appp=round(ap['pp']), apuser=ap['name'])
    except:
        return await render_template('home.html', vnpp=0, vnuser="None", vndate=0, rxdate=0, apdate=0, rxpp=0, rxuser="None", appp=0, apuser="None")

@frontend.route('/home/account/edit')
async def home_account_edit():
    return redirect('/settings/profile')

@frontend.route('/settings')
@frontend.route('/settings/profile')
@login_required
async def settings_profile():
    return await render_template('settings/profile.html')

@frontend.route('/settings/profile', methods=['POST'])
@login_required
async def settings_profile_post():
    form = await request.form

    new_name = form.get('username', type=str)
    new_email = form.get('email', type=str)

    if new_name is None or new_email is None:
        return await flash('error', 'Invalid parameters.', 'home')

    old_name = session['user_data']['name']
    old_email = session['user_data']['email']

    # no data has changed; deny post
    if (
        new_name == old_name and
        new_email == old_email
    ):
        return await flash('error', 'No changes have been made.', 'settings/profile')

    if new_name != old_name:
        if not session['user_data']['is_donator'] or not session['user_data']['is_staff']:
            return await flash('error', 'Username changes are currently a supporter perk.', 'settings/profile')

        # Usernames must:
        # - be within 2-15 characters in length
        # - not contain both ' ' and '_', one is fine
        # - not be in the config's `disallowed_names` list
        # - not already be taken by another player
        if not regexes.username.match(new_name):
            return await flash('error', 'Your new username syntax is invalid.', 'settings/profile')

        if '_' in new_name and ' ' in new_name:
            return await flash('error', 'Your new username may contain "_" or " ", but not both.', 'settings/profile')

        if new_name in glob.config.disallowed_names:
            return await flash('error', "Your new username isn't allowed; pick another.", 'settings/profile')

        if await glob.db.fetch('SELECT 1 FROM users WHERE name = %s', [new_name]):
            return await flash('error', 'Your new username already taken by another user.', 'settings/profile')

        safe_name = utils.get_safe_name(new_name)

        # username change successful
        await glob.db.execute(
            'UPDATE users '
            'SET name = %s, safe_name = %s '
            'WHERE id = %s',
            [new_name, safe_name, session['user_data']['id']]
        )

    if new_email != old_email:
        # Emails must:
        # - match the regex `^[^@\s]{1,200}@[^@\s\.]{1,30}\.[^@\.\s]{1,24}$`
        # - not already be taken by another player
        if not regexes.email.match(new_email):
            return await flash('error', 'Your new email syntax is invalid.', 'settings/profile')

        if await glob.db.fetch('SELECT 1 FROM users WHERE email = %s', [new_email]):
            return await flash('error', 'Your new email already taken by another user.', 'settings/profile')

        # email change successful
        await glob.db.execute(
            'UPDATE users '
            'SET email = %s '
            'WHERE id = %s',
            [new_email, session['user_data']['id']]
        )

    # logout
    session.pop('authenticated', None)
    session.pop('user_data', None)
    return await flash('success', 'Your username/email have been changed! Please login again.', 'login')

@frontend.route('/settings/avatar')
@login_required
async def settings_avatar():
    return await render_template('settings/avatar.html')

@frontend.route('/settings/avatar', methods=['POST'])
@login_required
async def settings_avatar_post():
    # constants
    AVATARS_PATH = f'{glob.config.path_to_asahi}resources/avatars'
    ALLOWED_EXTENSIONS = ['.jpeg', '.jpg', '.png']

    avatar = (await request.files).get('avatar')

    # no file uploaded; deny post
    if avatar is None or not avatar.filename:
        return await flash('error', 'No image was selected!', 'settings/avatar')

    filename, file_extension = os.path.splitext(avatar.filename.lower())

    # bad file extension; deny post
    if not file_extension in ALLOWED_EXTENSIONS:
        return await flash('error', 'The image you select must be either a .JPG, .JPEG, or .PNG file!', 'settings/avatar')

    # remove old avatars
    if os.path.isfile(f'{AVATARS_PATH}/{session["user_data"]["id"]}'): # Checking file e
        os.remove(f'{AVATARS_PATH}/{session["user_data"]["id"]}')

    # avatar cropping to 1:1
    pilavatar = Image.open(avatar.stream)

    # avatar change success
    pilavatar = utils.crop_image(pilavatar)
    pilavatar.save(os.path.join(AVATARS_PATH, f'{session["user_data"]["id"]}.png'))
    os.rename(f'{AVATARS_PATH}/{session["user_data"]["id"]}.png',f'{AVATARS_PATH}/{session["user_data"]["id"]}')
    return await flash('success', 'Your avatar has been successfully changed!', 'settings/avatar')

@frontend.route('/settings/custom')
@login_required
async def settings_custom():
    profile_customizations = utils.has_profile_customizations(session['user_data']['id'])
    return await render_template('settings/custom.html', customizations=profile_customizations)

@frontend.route('/settings/custom', methods=['POST'])
@login_required
async def settings_custom_post():
    banner = (await request.files).get('banner')
    background = (await request.files).get('background')
    ALLOWED_EXTENSIONS = ['.jpeg', '.jpg', '.png', '.gif']

    # no file uploaded; deny post
    if banner is None and background is None:
        return await flash_with_customizations('error', 'No image was selected!', 'settings/custom')

    if banner is not None and banner.filename:
        filename, file_extension = os.path.splitext(banner.filename.lower())
        if not file_extension in ALLOWED_EXTENSIONS:
            return await flash_with_customizations('error', f'The banner you select must be either a .JPG, .JPEG, .PNG or .GIF file!', 'settings/custom')

        banner_file_no_ext = os.path.join(f'.data/banners', f'{session["user_data"]["id"]}')

        # remove old picture
        for ext in ALLOWED_EXTENSIONS:
            banner_file_with_ext = f'{banner_file_no_ext}{ext}'
            if os.path.isfile(banner_file_with_ext):
                os.remove(banner_file_with_ext)

        await banner.save(f'{banner_file_no_ext}{file_extension}')

    if background is not None and background.filename:
        filename, file_extension = os.path.splitext(background.filename.lower())
        if not file_extension in ALLOWED_EXTENSIONS:
            return await flash_with_customizations('error', f'The background you select must be either a .JPG, .JPEG, .PNG or .GIF file!', 'settings/custom')

        background_file_no_ext = os.path.join(f'.data/backgrounds', f'{session["user_data"]["id"]}')

        # remove old picture
        for ext in ALLOWED_EXTENSIONS:
            background_file_with_ext = f'{background_file_no_ext}{ext}'
            if os.path.isfile(background_file_with_ext):
                os.remove(background_file_with_ext)

        await background.save(f'{background_file_no_ext}{file_extension}')

    return await flash_with_customizations('success', 'Your customisation has been successfully changed!', 'settings/custom')


@frontend.route('/settings/password')
@login_required
async def settings_password():
    return await render_template('settings/password.html')

@frontend.route('/settings/password', methods=["POST"])
@login_required
async def settings_password_post():
    form = await request.form
    old_password = form.get('old_password')
    new_password = form.get('new_password')
    repeat_password = form.get('repeat_password')

    # new password and repeat password don't match; deny post
    if new_password != repeat_password:
        return await flash('error', "Your new password doesn't match your repeated password!", 'settings/password')

    # new password and old password match; deny post
    if old_password == new_password:
        return await flash('error', 'Your new password cannot be the same as your old password!', 'settings/password')

    # Passwords must:
    # - be within 8-32 characters in length
    # - have more than 3 unique characters
    # - not be in the config's `disallowed_passwords` list
    if not 8 < len(new_password) <= 32:
        return await flash('error', 'Your new password must be 8-32 characters in length.', 'settings/password')

    if len(set(new_password)) <= 3:
        return await flash('error', 'Your new password must have more than 3 unique characters.', 'settings/password')

    if new_password.lower() in glob.config.disallowed_passwords:
        return await flash('error', 'Your new password was deemed too simple.', 'settings/password')

    # cache and other password related information
    pw_cache = glob.cache['pw']
    pw_hash = (await glob.db.fetchval(
        'SELECT pw '
        'FROM users '
        'WHERE id = %s',
        [session['user_data']['id']])
    ).encode('ISO-8859-1').decode('unicode-escape').encode('ISO-8859-1')

    pw_md5 = hashlib.md5(old_password.encode()).hexdigest().encode()

    # check old password against db
    # intentionally slow, will cache to speed up
    if pw_hash in pw_cache:
        if pw_md5 != pw_cache[pw_hash]: # ~0.1ms
            if glob.config.debug:
                log(f"{session['user_data']['name']}'s change pw failed - pw incorrect.", Ansi.LYELLOW)
            return await flash('error', 'Your old password is incorrect.', 'settings/password')
    else: # ~200ms
        k = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b'', backend=backend())
        try:
            k.verify(pw_hash, pw_md5)
        except:
            if glob.config.debug:
                log(f"{session['user_data']['name']}'s change pw failed - pw incorrect.", Ansi.LYELLOW)
            return await flash('error', 'Your old password is incorrect.', 'settings/password')

    # remove old password from cache
    if pw_hash in pw_cache:
        del pw_cache[pw_hash]

    # calculate new md5 & bcrypt pw
    pw_md5 = hashlib.md5(new_password.encode()).hexdigest().encode()
    k = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b'', backend=backend())
    pw_hash_new = k.derive(pw_md5).decode('unicode-escape')

    # update password in cache and db
    pw_cache[pw_hash_new] = pw_md5
    await glob.db.execute(
        'UPDATE users '
        'SET pw = %s '
        'WHERE safe_name = %s',
        [pw_hash_new, utils.get_safe_name(session['user_data']['name'])]
    )

    # logout
    session.pop('authenticated', None)
    session.pop('user_data', None)
    return await flash('success', 'Your password has been changed! Please log in again.', 'login')

@frontend.route('/u/<user>')
async def profile(user):
    mode = request.args.get('mode', type=str)
    mods = request.args.get('mods', type=str)

    # make sure mode & mods are valid args
    if mode is not None:
        if mode not in VALID_MODES:
            return (await render_template('404.html'), 404)
    else:
        mode = 'std'

    if mods is not None:
        if mods not in VALID_MODS:
            return (await render_template('404.html'), 404)
    else:
        mods = 'vn'

    user_data = await glob.db.fetchrow("SELECT name, id, priv, country, freeze_timer FROM users WHERE id = %s OR safe_name = %s", [user, utils.get_safe_name(user)])

    # user is banned and we're not staff; render 404
    if not user_data or (user_data['priv'] & Privileges.Disallowed):
        return (await render_template('404.html'), 404)

    user_data['customisation'] = utils.has_profile_customizations(id)
    
    
    freezeinfo = [bool(user_data['priv'] & Privileges.Frozen), timeago.format(datetime.fromtimestamp(user_data['freeze_timer']), datetime.now())]
    if await glob.db.fetch('SELECT 1 FROM user_badges WHERE uid = %s', [user_data['id']]):
        badges = True
        defbadges = await glob.db.fetch("SELECT bid, badges.name, badges.color, badges.icon FROM user_badges LEFT JOIN badges ON user_badges.bid = badges.id WHERE uid = %s", [user_data['id']])
    else:
        badges = None
        defbadges = None

    return await render_template('profile.html', user=user_data, mode=mode, mods=mods, country=(pycountry.countries.get(alpha_2=user_data['country'])).name, ub=badges, bi=defbadges, freeze=freezeinfo)

@frontend.route('/leaderboard')
@frontend.route('/lb')
@frontend.route('/leaderboard/<mode>/<mods>')
@frontend.route('/lb/<mode>/<mods>')
async def leaderboard(mode='std', mods='vn'):
    return await render_template('leaderboard.html', mode=mode, mods=mods)

@frontend.route('/login')
async def login():
    if 'authenticated' in session:
        return await flash('error', "You're already logged in!", 'home')

    return await render_template('login.html')

@frontend.route('/login', methods=['POST'])
async def login_post():
    if 'authenticated' in session:
        return await flash('error', "You're already logged in!", 'home')

    if glob.config.debug:
        login_time = time.time_ns()

    form = await request.form
    username = form.get('username', type=str)
    passwd_txt = form.get('password', type=str)

    if username is None or passwd_txt is None:
        return await flash('error', 'Invalid parameters.', 'home')

    # check if account exists
    user_info = await glob.db.fetchrow(
        'SELECT id, name, email, priv, '
        'pw, silence_end '
        'FROM users '
        'WHERE safe_name = %s',
        [utils.get_safe_name(username)]
    )

    # user doesn't exist; deny post
    # NOTE: Bot isn't a user.
    if not user_info or user_info['id'] == 1:
        if glob.config.debug:
            log(f"{username}'s login failed - account doesn't exist.", Ansi.LYELLOW)
        return await flash('error', 'Account does not exist.', 'login')

    # cache and other related password information
    pw_cache = glob.cache['pw']
    pw_hash = user_info['pw'].encode('ISO-8859-1').decode('unicode-escape').encode('ISO-8859-1')
    pw_md5 = hashlib.md5(passwd_txt.encode()).hexdigest().encode()

    # check credentials (password) against db
    # intentionally slow, will cache to speed up
    if pw_hash in pw_cache:
        if pw_md5 != pw_cache[pw_hash]: # ~0.1ms
            if glob.config.debug:
                log(f"{username}'s login failed - pw incorrect.", Ansi.LYELLOW)
            return await flash('error', 'Password is incorrect.', 'login')
    else: # ~200ms
        k = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b'', backend=backend())
        try:
           k.verify(pw_md5, pw_hash)
        except:
            if glob.config.debug:
                log(f"{username}'s login failed - pw incorrect.", Ansi.LYELLOW)
            return await flash('error', 'Password is incorrect.', 'login')

        # login successful; cache password for next login
        pw_cache[pw_hash] = pw_md5

    # user not verified; render verify
    if not user_info['priv'] & Privileges.Verified:
        if glob.config.debug:
            log(f"{username}'s login failed - not verified.", Ansi.LYELLOW)
        return await render_template('verify.html')

    # user banned; deny post
    if user_info['priv'] & Privileges.Disallowed:
        if glob.config.debug:
            log(f"{username}'s login failed - banned.", Ansi.RED)
        return await flash('error', 'Your account is restricted. You are not allowed to log in.', 'login')

    # login successful; store session data
    if glob.config.debug:
        log(f"{username}'s login succeeded.", Ansi.LGREEN)

    session['authenticated'] = True
    session['user_data'] = {
        'id': user_info['id'],
        'name': user_info['name'],
        'email': user_info['email'],
        'priv': user_info['priv'],
        'silence_end': user_info['silence_end'],
        'is_staff': user_info['priv'] & Privileges.Staff,
        'is_donator': user_info['priv'] & Privileges.Supporter
    }

    if glob.config.debug:
        login_time = (time.time_ns() - login_time) / 1e6
        log(f'Login took {login_time:.2f}ms!', Ansi.LYELLOW)

    return await flash('success', f'Hey, welcome back {username}!', 'home')

@frontend.route('/register')
async def register():
    if 'authenticated' in session:
        return await flash('error', "You're already logged in.", 'home')

    if not glob.config.registration:
        return await flash('error', 'Registrations are currently disabled.', 'home')

    return await render_template('register.html')

@frontend.route('/register', methods=['POST'])
async def register_post():
    if 'authenticated' in session:
        return await flash('error', "You're already logged in.", 'home')

    if not glob.config.registration:
        return await flash('error', 'Registrations are currently disabled.', 'home')

    form = await request.form
    username = form.get('username', type=str)
    email = form.get('email', type=str)
    passwd_txt = form.get('password', type=str)

    if username is None or email is None or passwd_txt is None:
        return await flash('error', 'Invalid parameters.', 'home')

    if glob.config.hCaptcha_sitekey != 'changeme':
        captcha_data = form.get('h-captcha-response', type=str)
        if (
            captcha_data is None or
            not await utils.validate_captcha(captcha_data)
        ):
            return await flash('error', 'Captcha failed.', 'register')

    # Usernames must:
    # - be within 2-15 characters in length
    # - not contain both ' ' and '_', one is fine
    # - not be in the config's `disallowed_names` list
    # - not already be taken by another player
    # check if username exists
    if not regexes.username.match(username):
        return await flash('error', 'Invalid username syntax.', 'register')

    if '_' in username and ' ' in username:
        return await flash('error', 'Username may contain "_" or " ", but not both.', 'register')

    if username in glob.config.disallowed_names:
        return await flash('error', 'Disallowed username; pick another.', 'register')

    if await glob.db.fetch('SELECT 1 FROM users WHERE name = %s', username):
        return await flash('error', 'Username already taken by another user.', 'register')

    # Emails must:
    # - match the regex `^[^@\s]{1,200}@[^@\s\.]{1,30}\.[^@\.\s]{1,24}$`
    # - not already be taken by another player
    if not regexes.email.match(email):
        return await flash('error', 'Invalid email syntax.', 'register')

    if await glob.db.fetch('SELECT 1 FROM users WHERE email = %s', email):
        return await flash('error', 'Email already taken by another user.', 'register')

    # Passwords must:
    # - be within 8-32 characters in length
    # - have more than 3 unique characters
    # - not be in the config's `disallowed_passwords` list
    if not 8 <= len(passwd_txt) <= 32:
        return await flash('error', 'Password must be 8-32 characters in length.', 'register')

    if len(set(passwd_txt)) <= 3:
        return await flash('error', 'Password must have more than 3 unique characters.', 'register')

    if passwd_txt.lower() in glob.config.disallowed_passwords:
        return await flash('error', 'That password was deemed too simple.', 'register')

    # TODO: add correct locking
    # (start of lock)
    pw_md5 = hashlib.md5(passwd_txt.encode()).hexdigest().encode()
    k = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b'', backend=backend())
    pw_hash = k.derive(pw_md5).decode('unicode-escape')
    glob.cache['pw'][pw_hash] = pw_md5 # cache pw

    safe_name = utils.get_safe_name(username)

    # fetch the users' country
    if 'CF-Connecting-IP' in request.headers:
        ip = request.headers['CF-Connecting-IP']
    else:
        ip = request.headers['X-Forwarded-For'].split(',')[0]
    
    try:
        country = await utils.fetch_geoloc(ip)
    except:
        country = 'xx'

    user = await glob.db.execute(
        'INSERT INTO users '
        '(name, safe_name, email, pw, country, registered_at) '
        'VALUES (%s, %s, %s, %s, %s, UNIX_TIMESTAMP())',
        [username, safe_name, email, pw_hash, country]
    )
        
    user_id = user

    # add to `stats` table.
    await glob.db.execute(
        'INSERT INTO stats '
        '(id) VALUES (%s)',
        user_id
    )

    # (end of lock)

    if glob.config.debug:
        log(f'{username} has registered - awaiting verification.', Ansi.LGREEN)

    # user has successfully registered
    return await render_template('verify.html')

@frontend.route('/logout')
async def logout():
    if 'authenticated' not in session:
        return await flash('error', "You can't logout if you aren't logged in!", 'login')

    if glob.config.debug:
        log(f'{session["user_data"]["name"]} logged out.', Ansi.LGREEN)

    # clear session data
    session.pop('authenticated', None)
    session.pop('user_data', None)

    # render login
    return await flash('success', 'Successfully logged out!', 'login')
    
@frontend.route('/rules')
async def rules():
    return await render_template('rules.html')

# social media redirections

@frontend.route('/github')
@frontend.route('/gh')
async def github_redirect():
    return redirect(glob.config.github)

@frontend.route('/discord')
async def discord_redirect():
    return redirect(glob.config.discord_server)

@frontend.route('/youtube')
@frontend.route('/yt')
async def youtube_redirect():
    return redirect(glob.config.youtube)

@frontend.route('/twitter')
async def twitter_redirect():
    return redirect(glob.config.twitter)

@frontend.route('/instagram')
@frontend.route('/ig')
async def instagram_redirect():
    return redirect(glob.config.instagram)

# profile customisation
BANNERS_PATH = Path.cwd() / '.data/banners'
BACKGROUND_PATH = Path.cwd() / '.data/backgrounds'
@frontend.route('/banners/<user_id>')
async def get_profile_banner(user_id: int):
    # Check if avatar exists
    for ext in ('jpg', 'jpeg', 'png', 'gif'):
        path = BANNERS_PATH / f'{user_id}.{ext}'
        if path.exists():
            return await send_file(path)

    return b'{"status":404}'


@frontend.route('/backgrounds/<user_id>')
async def get_profile_background(user_id: int):
    # Check if avatar exists
    for ext in ('jpg', 'jpeg', 'png', 'gif'):
        path = BACKGROUND_PATH / f'{user_id}.{ext}'
        if path.exists():
            return await send_file(path)

    return b'{"status":404}'
