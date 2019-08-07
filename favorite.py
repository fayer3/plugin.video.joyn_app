# -*- coding: utf-8 -*-

import logging
import json

import xbmcaddon
import xbmcvfs
import xbmc

from resources.lib import kodiutils
from resources.lib import kodilogging

try:
    from urllib.parse import quote, unquote, quote_plus, unquote_plus
except ImportError:
    from urllib import quote, unquote, quote_plus, unquote_plus

def log(info):
    if kodiutils.get_setting_as_bool("debug"):
        logger.warning(info.decode('ascii', 'ignore').encode('ascii','ignore'))

logger = logging.getLogger(xbmcaddon.Addon().getAddonInfo('id'))
kodilogging.config()

__profile__ = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))

if not xbmcvfs.exists(__profile__):
    xbmcvfs.mkdirs(__profile__)

favorites_file_path = __profile__+"favorites.json"

log('launched: favorit.py with {0} arguments'.format(len(sys.argv)))

log(str(sys.argv))

if len(sys.argv) > 1:
    if sys.argv[1] == 'add' and len(sys.argv) == 9:
        # get parameters
        path = unquote(sys.argv[2])
        name = unquote(sys.argv[3])
        log('add favorite: {0}, {1}'.format(path, name))
        desc = unquote_plus(sys.argv[4])
        icon = unquote(sys.argv[5])
        poster = unquote(sys.argv[6])
        thumbnail = unquote(sys.argv[7])
        fanart = unquote(sys.argv[8])

        # load favorites
        favorites = {}
        if not favorites and xbmcvfs.exists(favorites_file_path):
            favorites_file = xbmcvfs.File(favorites_file_path)
            favorites = json.load(favorites_file)
            favorites_file.close()

        favorites.update({path : {'name': name, 'desc': desc, 'icon': icon, 'poster': poster, 'thumbnail': thumbnail, 'fanart': fanart}})
        # save favorites
        favorites_file = xbmcvfs.File(favorites_file_path, 'w')
        json.dump(favorites, favorites_file, indent=2)
        favorites_file.close()

        kodiutils.notification(kodiutils.get_string(32011), kodiutils.get_string(32012).format(name))
        xbmc.executebuiltin('Container.Refresh')
    elif sys.argv[1] == 'remove' and len(sys.argv) == 3:
        data = unquote(sys.argv[2])
        # load favorites
        favorites = {}
        if not favorites and xbmcvfs.exists(favorites_file_path):
            favorites_file = xbmcvfs.File(favorites_file_path)
            favorites = json.load(favorites_file)
            favorites_file.close()

        if data in favorites:
            name = favorites[data]['name']
            del favorites[data]
            # load favorites
            favorites_file = xbmcvfs.File(favorites_file_path, 'w')
            json.dump(favorites, favorites_file, indent=2)
            favorites_file.close()

            kodiutils.notification(kodiutils.get_string(32011), kodiutils.get_string(32013).format(name))
            xbmc.executebuiltin('Container.Refresh')
