
[![Discord](https://discordapp.com/api/guilds/833325274934411274/widget.png?style=shield)](https://discord.gg/d62tzSYv3z)

Table of Contents
==================
- [Table of Contents](#table-of-contents)
  - [What is asahi-web?](#what-is-asahi-web)
  - [Setup](#setup)
  - [Directory Structure](#directory-structure)
  - [The End](#the-end)

What is asahi-web?
------

asahi-web is the front-facing appearance of the osu! server protocol, [Asahi](https://github.com/tsunyoku/Asahi)!

It's a project by me, that uses [guweb](https://github.com/Varkaria/guweb)'s source code, but is made to work with Asahi.

Using native async/await syntax written on top of [Quart](https://github.com/pgjones/quart) and
[cmyui's multipurpose library](https://github.com/cmyui/cmyui_pkg), asahi-web achieves flexability, cleanliness,
and efficiency not seen in other frontend implementations - all while maintaining the simplicity of Python.

A primary goal of asahi-web is to keep our codebase a developer-friendly API, so that
programming remains about the logic and ideas, rather than the code itself.

gulag-web is written by Yo-ru and Varkaria, but me and other contributors are mainly writing asahi-web.


Requirements
------

- Some know-how with Linux (tested on Ubuntu 18.04), Python, and general-programming knowledge.
- MySQL
- NGINX

Setup
------

Setup is relatively simple - these commands should set you right up.

Notes:

- Ubuntu 20.04 is known to have issues with NGINX and osu! for unknown reasons?
- If you have any difficulties setting up asahi-web, feel free to join the Discord server at the top of the README, we now have a bit of a community!

```sh
# Install Python >=3.9 and latest version of PIP.
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.9 python3.9-dev python3.9-distutils
wget https://bootstrap.pypa.io/get-pip.py
python3.9 get-pip.py && rm get-pip.py

# Install MySQL and NGINX.
sudo apt install mysql-server nginx

# Clone asahi-web from GitHub.
git clone https://github.com/7ez/asahi-web.git
cd asahi-web

# Initialize and update the submodules.
git submodule init && git submodule update

# Install requirements from pip.
python3.9 -m pip install -r ext/requirements.txt

# Add and configure asahi-web's NGINX config to your nginx/sites-enabled.
sudo ln -r -s ext/nginx.conf /etc/nginx/sites-enabled/asahi-web.conf
sudo nano ext/nginx.conf
sudo nginx -s reload

# Configure asahi-web.
cp ext/config.sample.py config.py
nano config.py

# Run asahi-web.
python3.9 main.py # Run directly to access debug features for development! (Port 5000)
hypercorn main.py # Please run asahi-web with hypercorn when in production! It will improve performance drastically by disabling all of the debug features a developer would need! (Port 8000)
```

Directory Structure
------

    .
    ├── blueprints   # Modular routes such as the API, Frontend, or Admin Panel.
    ├── docs         # Markdown files used in asahi-web's documentation system.
    ├── ext          # External files from asahi-web's primary operation.
    ├── objects      # Code for representing privileges, global objects, and more.
    ├── static       # Code or content that is not modified or processed by asahi-web itself.
    ├── templates    # HTML that contains content that is rendered after the page has loaded.
        ├── admin    # Templated content for the admin panel (/admin).
        ├── settings # Templated content for settings (/settings).
        └ ...         # Templated content for all of asahi-web (/).

The End
------
