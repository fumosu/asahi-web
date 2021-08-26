# -*- coding: utf-8 -*-

# app name
app_name = 'guweb'

# secret key
secret_key = 'changeme'

#hCaptcha settings:
hCaptcha_sitekey = 'changeme'
hCaptcha_secret = 'changeme'

# domain (used for api, avatar, etc)
domain = 'gulag.ca'

# mysql credentials
mysql = {
    'db': 'gulag',
    'host': 'localhost',
    'user': 'cmyui',
    'password': 'changeme',
}

# path to asahi root (must have leading and following slash)
path_to_asahi = '/path/to/asahi/'

# enable debug (disable when in production to improve performance)
debug = False

# disallowed names (hardcoded banned usernames)
disallowed_names = {
    'cookiezi', 'rrtyui',
    'hvick225', 'qsc20010'
}

# disallowed passwords (hardcoded banned passwords)
disallowed_passwords = {
    'password', 'minilamp'
}

# enable registration
registration = True

# social links (used throughout asahi-web)
github = 'https://github.com/7ez/asahi-web'
discord_server = 'https://discord.com/invite/d62tzSYv3z'
youtube = 'https://youtube.com/'
twitter = 'https://twitter.com/'
instagram = 'https://instagram.com/'
