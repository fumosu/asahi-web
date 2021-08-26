# -*- coding: utf-8 -*-

__all__ = ('db', 'http', 'version', 'cache')

from typing import TYPE_CHECKING

import config  # imported for indirect use

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from fatFuckSQL import fatFawkSQL
    from cmyui.version import Version

db: 'fatFawkSQL'
http: 'ClientSession'
version: 'Version'

cache = {
    'pw': {}
}
