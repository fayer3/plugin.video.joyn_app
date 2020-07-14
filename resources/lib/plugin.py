# -*- coding: utf-8 -*-

import routing
import logging
import xbmcaddon
import xbmcgui
import xbmcvfs
import xbmc
import xbmcplugin

from xbmcgui import ListItem
from xbmcplugin import addDirectoryItem, addDirectoryItems, endOfDirectory, setResolvedUrl, setContent

from resources.lib import kodiutils
from resources.lib import kodilogging
from resources.lib import ids
from resources.lib import xxtea

from distutils.version import LooseVersion
from datetime import datetime, timedelta, date

import pytz
import tzlocal

import codecs
import locale
import time
import hashlib
import json
import gzip
import sys
import re
import base64
import random
import uuid

try:
    import inputstreamhelper
    inputstream = True
except ImportError:
    inputstream = False

try:
    from multiprocessing.pool import ThreadPool
    multiprocess = True
except ImportError:
    multiprocess = False

# import of modules that are different between PY2 and PY3
try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO

try:
    from urllib.request import Request, urlopen, build_opener, ProxyHandler
    from urllib.error import HTTPError, URLError
    from urllib.parse import quote, unquote
except ImportError:
    from urllib import quote, unquote
    from urllib2 import Request, urlopen, HTTPError, URLError, build_opener, ProxyHandler

try:
    from html.parser import HTMLParser
except ImportError:
    from HTMLParser import HTMLParser
html_parser = HTMLParser()

ADDON = xbmcaddon.Addon()
logger = logging.getLogger(ADDON.getAddonInfo('id'))
kodilogging.config()
plugin = routing.Plugin()

__profile__ = xbmc.translatePath(ADDON.getAddonInfo('profile'))
ADDON_PATH = xbmc.translatePath(ADDON.getAddonInfo('path'))

if not xbmcvfs.exists(__profile__):
    xbmcvfs.mkdirs(__profile__)

favorites_file_path = __profile__+"favorites.json"
favorites = {}

icon_path = ADDON.getAddonInfo('path')+"/resources/icons/{0}.png"
setContent(plugin.handle, 'tvshows')
#setContent(plugin.handle, '')

@plugin.route('/')
def index():
    check = kodiutils.get_setting_as_int('update_check')
    if check < 2:
        content = get_url(ids.joyn_update_url, key=False)
        if content:
            content = json.loads(content)
            if 'updateAlert' in content and content['updateAlert']['active'] == True and content['updateAlert']['allowAppStart'] == False:
                if check == 1 or kodiutils.get_setting('last_update_warning') != ids.joyn_version:
                    xbmcgui.Dialog().ok(kodiutils.get_string(32019), kodiutils.get_string(32020))
                    kodiutils.set_setting('last_update_warning', ids.joyn_version)
    #content = json.loads(get_url(ids.overview_url, critical = True))
    content = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.overview_variables,query = ids.overview_query), key = True, json = True, critical = True))
    for item in content['data']['page']['blocks']:
        if item['__typename'] != 'ResumeLane' and item['__typename'] != 'BookmarkLane' and item['__typename'] != 'RecoForYouLane':
            name = 'Folder'
            if 'headline' in item:
                name = item['headline']
            elif item['__typename'] == 'HeroLane':
                name = kodiutils.get_string(32001)
            addDirectoryItem(plugin.handle,plugin.url_for(
                show_fetch, fetch_id=item['id'], type=item['__typename']), ListItem(name), True)
    addDirectoryItem(plugin.handle, plugin.url_for(
        show_epg), ListItem('EPG'), True)
    addDirectoryItem(plugin.handle, plugin.url_for(
        search), ListItem(kodiutils.get_string(32014)), True)
    addDirectoryItem(plugin.handle, plugin.url_for(
        show_category, 'favorites'), ListItem(kodiutils.get_string(32007)), True)
    addDirectoryItem(plugin.handle, plugin.url_for(
        open_settings), ListItem(kodiutils.get_string(32008)))
    endOfDirectory(plugin.handle)

@plugin.route('/search')
def search():
    query = xbmcgui.Dialog().input(kodiutils.get_string(32014))
    if query != '':
        #content = json.loads(get_url(ids.search_url.format(search=quote(query)), critical = True))
        content = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.search_variables.format(search=query),query = ids.search_query), key = True, json = True, critical = True))
        if('data' in content and 'search' in content['data'] and 'results' in content['data']['search']):
            add_from_fetch(content['data']['search']['results'])
    endOfDirectory(plugin.handle)

@plugin.route('/epg')
def show_epg():
    content = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.livestream_variables,query = ids.livestream_query), key = True, json = True, critical = True))
    #content = json.loads(get_url(ids.epg_now_url, key = False, headers = {'key':ids.middleware_token}, critical = True))
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_LABEL)
    #log(json.dumps(content))
    for channel in content['data']['brands']:
        if 'livestream' in channel and channel['livestream'] != None:
            listitem = ListItem(channel['title'])
            logo = ''
            if 'logo' in channel and channel['logo'] != None:
                logo = ids.image_url.format(channel['logo']['url'])
            listitem.setArt({'icon': logo, 'thumb': logo, 'poster': logo})
            addDirectoryItem(plugin.handle,plugin.url_for(
                show_channel_epg, channel_id=channel['id'], offset=0), listitem, True)
    endOfDirectory(plugin.handle)

@plugin.route('/epg/id=<channel_id>/offset=<offset>')
def show_channel_epg(channel_id, offset):
    content = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.epg_variables.format(brandId = channel_id, offset = offset),query = ids.epg_query), key = True, json = True, critical = True))
    if 'livestream' in content['data']['brand'] and content['data']['brand']['livestream'] != None and 'epg' in content['data']['brand']['livestream'] and content['data']['brand']['livestream']['epg'] != None and len(content['data']['brand']['livestream']['epg']) >0:
        for epg in content['data']['brand']['livestream']['epg']:
            addDirectoryItem(plugin.handle, plugin.url_for(show_info), get_epg_listitem(epg, start_in_label = True))
        addDirectoryItem(plugin.handle, plugin.url_for(show_channel_epg, channel_id = channel_id, offset = int(offset)+25), ListItem(kodiutils.get_string(32033)),True)
    else:
        addDirectoryItem(plugin.handle, '', ListItem(kodiutils.get_string(32034)))
    endOfDirectory(plugin.handle)

def get_epg_listitem(epgdata, start_in_label = False):
    infoLabels = {}
    art = {}
    infoLabels.update({'title': epgdata['secondaryTitle'] if epgdata['secondaryTitle'] != None and epgdata['secondaryTitle'] != '' else epgdata['title']})
    infoLabels.update({'tvShowTitle': epgdata['title']})

    local_start_time = datetime.fromtimestamp(epgdata['startDate'])
    local_end_time = datetime.fromtimestamp(epgdata['endDate'])
    plot = u'[COLOR chartreuse]{0} - {1}[/COLOR]'.format(local_start_time.strftime('%H:%M'), local_end_time.strftime('%H:%M'))
    plot += u'[CR][CR]'
    infoLabels.update({'plot': plot})

    if 'images' in epgdata and epgdata['images'] != None and len(epgdata['images']) > 0:
        for image in epgdata['images']:
            if image['type'] == 'LIVE_STILL':
                art.update({'fanart': ids.image_url.format(image['url'])})
                art.update({'thumb': ids.image_url.format(image['url'])})

    infoLabels.update({'mediatype': 'episode'})

    label = u''
    label = infoLabels.get('tvShowTitle') if not infoLabels.get('title') or infoLabels.get('tvShowTitle') == infoLabels.get('title') else u'[COLOR blue]{0}[/COLOR]  {1}'.format(infoLabels.get('tvShowTitle'), infoLabels.get('title'))
    if start_in_label:
        label = u'[COLOR chartreuse]{0}[/COLOR]: '.format(local_start_time.strftime('%H:%M')) + label

    listitem = ListItem(label)
    listitem.setArt(art)
    listitem.setInfo(type='Video', infoLabels=infoLabels)
    return listitem

@plugin.route('/info')
def show_info():
    xbmc.executebuiltin('Action(Info)')

@plugin.route('/fetch/id=<fetch_id>/type=<type>')
def show_fetch(fetch_id, type):
    i = 0
    while True:
        #content = json.loads(get_url(ids.fetch_url.format(blockId=fetch_id, offset = ids.offset*i), critical=True))
        content = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.fetch_variables.format(blockId=fetch_id, offset = ids.offset*i), query = ids.fetch_query), key = True, json = True, critical=False))
        if('data' in content and 'block' in content['data'] and 'assets' in content['data']['block']):
            if content['data']['block']['__typename'] == 'LiveLane':
                add_livestreams();
                endOfDirectory(plugin.handle)
                return
            add_from_fetch(content['data']['block']['assets'])
        else:
            break
        if len(content['data']['block']['assets']) != ids.offset:
            break
        i += 1
    endOfDirectory(plugin.handle)

def add_from_fetch(content):
    for asset in content:
        if asset['__typename'] == 'Series':
            add_series(asset)
        elif asset['__typename'] == 'Brand':
            add_tvchannel(asset)
        elif asset['__typename'] == 'EpgEntry':
            add_livestream(asset)
        elif asset['__typename'] == 'Compilation':
            add_compilation(asset)
        elif asset['__typename'] == 'Movie':
            add_movie(asset)
        else:
            kodiutils.notification("ERROR", "unknown type " + asset['__typename'])
            log("unknown type " + asset['__typename'])
            log(json.dumps(asset))

def add_series(asset):
    name = ''
    name = asset['title']
    if asset['tagline']:
        name += u': ' + asset['tagline']
    if len(asset['licenseTypes']) == 1 and 'SVOD' in asset['licenseTypes']:
        svod = kodiutils.get_setting_as_int('svod')
        if svod == 2:
            return
        if svod == 0:
            name = u'[PLUS+] ' + name
    Note_2 = u''
    description = asset['description']
    if 'ageRating' in asset and asset['ageRating'] != None:
        age = asset['ageRating']['minAge']
        if kodiutils.get_setting_as_bool('age_in_description'):
            Note_2 += kodiutils.get_string(32037).format(age)
    if 'copyrights' in asset and asset['copyrights'] != None and len(asset['copyrights']) > 0:
        if kodiutils.get_setting_as_bool('copyright_in_description'):
            Note_2 += kodiutils.get_string(32038).format(', '.join(asset['copyrights']))
    if Note_2:
        description = description + '[CR][CR]' + Note_2
    listitem = ListItem(name)
    # get images
    icon=''
    poster = ''
    fanart = ''
    thumbnail = ''
    for image in asset['images']:
        if image['type'] == 'PRIMARY':
            thumbnail = ids.image_url.format(image['url'])
        elif image['type'] == 'ART_LOGO':
            icon = ids.image_url.format(image['url'])
        elif image['type'] == 'HERO_LANDSCAPE':
            fanart = ids.image_url.format(image['url'])
        elif image['type'] == 'HERO_PORTRAIT':
            poster = ids.image_url.format(image['url'])
    if not poster and thumbnail:
        poster = thumbnail
    if not fanart and thumbnail:
        fanart = thumbnail
    if not fanart and thumbnail:
        icon = thumbnail
    listitem.setArt({'icon': icon, 'thumb': thumbnail, 'poster': poster, 'fanart': fanart})
    listitem.setInfo(type='Video', infoLabels={'Title': name, 'Plot': description, 'TvShowTitle': name})
    add_favorites_context_menu(listitem, plugin.url_for(
        show_seasons, show_id=asset['id']), name, asset['description'], icon, poster, thumbnail, fanart)
    addDirectoryItem(plugin.handle, plugin.url_for(
        show_seasons, show_id=asset['id']), listitem, True)

def add_tvchannel(asset):
    #log(json.dumps(content))
    listitem = ListItem(asset['title'])
    # get images
    icon = ids.image_url.format(asset['logo']['url'])
    listitem.setArt({'icon': icon, 'thumb': icon, 'poster': icon})
    listitem.setInfo(type='Video', infoLabels={'Title': asset['title'], 'TvShowTitle': asset['title']})
    addDirectoryItem(plugin.handle,plugin.url_for(
        show_channel, channel_path=quote(asset['path'], safe='')), listitem, True)

def add_compilation(asset):
    listitem = ListItem(asset['title'])
    description = u''
    if 'description' in asset and asset['description'] != None:
        description = asset['description']
    else:
        details = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.compilation_details_variables.format(id = asset['id']), query = ids.compilation_details_query), key = True, json = True, critical=False))
        #details = json.loads(post_url(ids.post_url, ids.compilation_details_post.format(id = asset['id']), key = True, json = True, critical=False))
        if details and 'data' in details and 'compilation' in details['data'] and 'description' in details['data']['compilation']:
            description = details['data']['compilation']['description']
    Note_2 = u''
    if 'ageRating' in asset and asset['ageRating'] != None:
        age = asset['ageRating']['minAge']
        if kodiutils.get_setting_as_bool('age_in_description'):
            Note_2 += kodiutils.get_string(32037).format(age)
    if 'copyrights' in asset and asset['copyrights'] != None and len(asset['copyrights']) > 0:
        if kodiutils.get_setting_as_bool('copyright_in_description'):
            Note_2 += kodiutils.get_string(32038).format(', '.join(asset['copyrights']))
    if Note_2:
        description = description + '[CR][CR]' + Note_2
    
    # get images
    icon=''
    poster = ''
    fanart = ''
    thumbnail = ''
    for image in asset['images']:
        if image['type'] == 'PRIMARY':
            thumbnail = ids.image_url.format(image['url'])
        elif image['type'] == 'ART_LOGO':
            icon = ids.image_url.format(image['url'])
        elif image['type'] == 'HERO_LANDSCAPE':
            fanart = ids.image_url.format(image['url'])
        elif image['type'] == 'HERO_PORTRAIT':
            poster = ids.image_url.format(image['url'])
    if not poster and thumbnail:
        poster = thumbnail
    if not fanart and thumbnail:
        fanart = thumbnail
    if not fanart and thumbnail:
        icon = thumbnail
    listitem.setArt({'icon': icon, 'thumb': thumbnail, 'poster': poster, 'fanart': fanart})
    listitem.setInfo(type='Video', infoLabels={'Title': asset['title'], 'Plot': description})
    add_favorites_context_menu(listitem, plugin.url_for(
        show_compilation, compilation_id=asset['id']), asset['title'], u'', icon, poster, thumbnail, fanart)
    addDirectoryItem(plugin.handle, plugin.url_for(
        show_compilation, compilation_id=asset['id']), listitem, True)

def add_livestream(asset):
    brand = u''
    infoLabels = {}
    art = {}
    brand = asset['livestream']['brand']['title']
    infoLabels.update({'title': asset['secondaryTitle'] if asset['secondaryTitle'] else asset['title']})
    infoLabels.update({'tvShowTitle': asset['title']})

    local_start_time = datetime.fromtimestamp(asset['startDate'])
    local_end_time = datetime.fromtimestamp(asset['endDate'])
    plot = '{0} - {1}'.format(local_start_time.strftime('%H:%M'), local_end_time.strftime('%H:%M'))

    plot += u'[CR][CR]'
    infoLabels.update({'plot': plot})

    
    icon = ids.image_url.format(asset['livestream']['brand']['logo']['url'])
    art.update({'icon': icon, 'thumb': icon})
    if len(asset['images']) > 0 and kodiutils.get_setting_as_bool('live_preview_for_icon'):
        for image in asset['images']:
            if image['type'] == 'LIVE_STILL':
                art.update({'fanart': ids.image_url.format(image['url'])})
                art.update({'thumb': ids.image_url.format(image['url'])})

    if infoLabels.get('title') and infoLabels.get('tvShowTitle') and infoLabels.get('title') != infoLabels.get('tvShowTitle'):
        infoLabels.update({'mediatype': 'episode'})
    else:
        # also use episode, because with 'video' it's not possible to view information
        infoLabels.update({'mediatype': 'episode'})
    label = u''
    if brand != infoLabels.get('tvShowTitle'):
        label = infoLabels.get('tvShowTitle') if not infoLabels.get('title') or infoLabels.get('tvShowTitle') == infoLabels.get('title') else u'[COLOR blue]{0}[/COLOR]  {1}'.format(infoLabels.get('tvShowTitle'), infoLabels.get('title'))
        label = u'[COLOR lime]{0}[/COLOR]  {1}'.format(brand, label)
        if kodiutils.get_setting_as_bool('channel_name_in_stream_title') and kodiutils.get_setting_as_bool('live_show_in_label'):
            infoLabels['title'] = label
    else:
        label = brand

    if not kodiutils.get_setting_as_bool('live_show_in_label'):
        label = brand
        infoLabels.update({'plot': u'{0}[CR]{1}'.format(infoLabels.get('tvShowTitle') if not infoLabels.get('title') or infoLabels.get('tvShowTitle') == infoLabels.get('title') else u'[COLOR blue]{0}[/COLOR]  {1}'.format(infoLabels.get('tvShowTitle'), infoLabels.get('title')), infoLabels.get('plot'))})
        if kodiutils.get_setting_as_bool('channel_name_in_stream_title'):
            infoLabels['title'] = u'[COLOR lime]{0}[/COLOR]  {1}'.format(brand, infoLabels.get('plot'))

    listitem = ListItem(label)
    listitem.setArt(art)
    listitem.setProperty('IsPlayable', 'true')
    listitem.setInfo(type='Video', infoLabels=infoLabels)
    addDirectoryItem(plugin.handle, plugin.url_for(
        play_live, stream_id=asset['livestream']['id'], brand=quote(brand.encode('ascii', 'xmlcharrefreplace'))), listitem)

def add_livestreams():
    livestreams = []

    #content = json.loads(get_url(ids.livestream_url, critical=True))
    content = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.livestream_variables,query = ids.livestream_query), key = True, json = True, critical = True))
    for item in content['data']['brands']:
        if not 'livestream' in item or item['livestream'] == None:
            continue
        epg_now = None
        epg_next = None
        if len(item['livestream']['epg']) > 1:
            epg_now = item['livestream']['epg'][0]
            epg_next = item['livestream']['epg'][1]
        elif len(item['livestream']['epg']) > 0:
            epg_now = item['livestream']['epg'][0]

        brand = item['title']
        infoLabels = {}
        art = {}
        if epg_now:
            infoLabels.update({'title': epg_now['secondaryTitle'] if epg_now['secondaryTitle'] else epg_now['title']})
            infoLabels.update({'tvShowTitle': epg_now['title']})

            local_start_time = datetime.fromtimestamp(epg_now['startDate'])
            local_end_time = datetime.fromtimestamp(epg_now['endDate'])
            plot = '{0} - {1}'.format(local_start_time.strftime('%H:%M'), local_end_time.strftime('%H:%M'))
            if epg_next:
                next_title = epg_next.get('secondaryTitle') if epg_next.get('secondaryTitle') else None
                next_show = epg_next.get('title') if epg_next.get('title') else u''

                plot += u'[CR]{0}: [COLOR blue]{1}[/COLOR] {2}'.format(kodiutils.get_string(32006), next_show, next_title) if next_title and next_show != u'' and next_title != next_show else u'[CR]{0}: {1}'.format(kodiutils.get_string(32006),next_title if next_title else next_show)

            plot += u'[CR][CR]'
            infoLabels.update({'plot': plot})

            icon = ids.image_url.format(item['logo']['url'])
            art.update({'icon': icon, 'thumb': icon})
            if len(epg_now['images']) > 0 and kodiutils.get_setting_as_bool('live_preview_for_icon'):
                for image in epg_now['images']:
                    if image['type'] == 'LIVE_STILL':
                        art.update({'fanart': ids.image_url.format(image['url'])})
                        art.update({'thumb': ids.image_url.format(image['url'])})
        else:
            brand = item['title']
            infoLabels.update({'title': brand})
            infoLabels.update({'tvShowTitle': brand})

            # get images
            icon = ids.image_url.format(item['logo']['url'])
            art.update({'icon': icon, 'thumb': icon, 'poster': icon})

        if infoLabels.get('title') and infoLabels.get('tvShowTitle') and infoLabels.get('title') != infoLabels.get('tvShowTitle'):
            infoLabels.update({'mediatype': 'episode'})
        else:
            # also use episode, because with 'video' it's not possible to view information
            infoLabels.update({'mediatype': 'episode'})
        label = u''
        if brand != infoLabels.get('tvShowTitle'):
            label = infoLabels.get('tvShowTitle') if not infoLabels.get('title') or infoLabels.get('tvShowTitle') == infoLabels.get('title') else u'[COLOR blue]{0}[/COLOR]  {1}'.format(infoLabels.get('tvShowTitle'), infoLabels.get('title'))
            label = u'[COLOR lime]{0}[/COLOR]  {1}'.format(brand, label)
            if kodiutils.get_setting_as_bool('channel_name_in_stream_title') and kodiutils.get_setting_as_bool('live_show_in_label'):
                infoLabels['title'] = label
        else:
            label = brand

        if not kodiutils.get_setting_as_bool('live_show_in_label'):
            label = brand
            infoLabels.update({'plot': u'{0}[CR]{1}'.format(infoLabels.get('tvShowTitle') if not infoLabels.get('title') or infoLabels.get('tvShowTitle') == infoLabels.get('title') else u'[COLOR blue]{0}[/COLOR]  {1}'.format(infoLabels.get('tvShowTitle'), infoLabels.get('title')), infoLabels.get('plot'))})
            if kodiutils.get_setting_as_bool('channel_name_in_stream_title'):
                infoLabels['title'] = u'[COLOR lime]{0}[/COLOR]  {1}'.format(brand, infoLabels.get('plot'))

        listitem = ListItem(label)
        listitem.setArt(art)
        listitem.setProperty('IsPlayable', 'true')
        listitem.setInfo(type='Video', infoLabels=infoLabels)
        livestreams.append((plugin.url_for(
            play_live, stream_id=item['livestream']['id'], brand=quote(brand.encode('ascii', 'xmlcharrefreplace'))), listitem))

    livestreams.sort(key=lambda x: x[1].getLabel().lower(), reverse=False)

    addDirectoryItems(plugin.handle, livestreams)

def add_movie(asset):
    infoLabels = {}
    Note_2 = u''
    infoLabels['mediatype'] = 'movie'
    name = ''
    name = asset['title']
    if asset['tagline']:
        name += u': ' + asset['tagline']
    infoLabels['Title'] = name
    if len(asset['licenseTypes']) == 1 and 'SVOD' in asset['licenseTypes']:
        svod = kodiutils.get_setting_as_int('svod')
        if svod == 2:
            return
        if svod == 0:
            name = u'[PLUS+] ' + name
    listitem = ListItem(name)
    # get images
    icon=''
    poster = ''
    fanart = ''
    thumbnail = ''
    for image in asset['images']:
        if image['type'] == 'PRIMARY':
            thumbnail = ids.image_url.format(image['url'])
        elif image['type'] == 'ART_LOGO':
            icon = ids.image_url.format(image['url'])
        elif image['type'] == 'HERO_LANDSCAPE':
            fanart = ids.image_url.format(image['url'])
        elif image['type'] == 'HERO_PORTRAIT':
            poster = ids.image_url.format(image['url'])
    if not poster and thumbnail:
        poster = thumbnail
    if not fanart and thumbnail:
        fanart = thumbnail
    if not fanart and thumbnail:
        icon = thumbnail
    
    if 'description' in asset and asset['description'] != None:
        infoLabels['Plot'] = asset['description']
    if 'genres' in asset and asset['genres'] != None:
        infoLabels['genre'] = []
        for genre in asset['genres']:
            infoLabels['genre'].append(genre['name'])
    if 'ageRating' in asset and asset['ageRating'] != None:
        infoLabels['mpaa'] = asset['ageRating']['minAge']
        if kodiutils.get_setting_as_bool('age_in_description'):
            Note_2 += kodiutils.get_string(32037).format(infoLabels['mpaa'])
    if 'copyrights' in asset and asset['copyrights'] != None and len(asset['copyrights']) > 0:
        if kodiutils.get_setting_as_bool('copyright_in_description'):
            Note_2 += kodiutils.get_string(32038).format(', '.join(asset['copyrights']))
    if Note_2:
        infoLabels['Plot'] = infoLabels['Plot'] + '[CR][CR]' + Note_2
    if 'productionYear' in asset and asset['productionYear'] != None:
        infoLabels['year'] = asset['productionYear']
        
    listitem.setArt({'icon': icon, 'thumb': thumbnail, 'poster': poster, 'fanart': fanart})
    listitem.setInfo(type='Video', infoLabels=infoLabels)
    listitem.setProperty('IsPlayable', 'true')
    listitem.addContextMenuItems([('Queue', 'Action(Queue)')])
    addDirectoryItem(plugin.handle, plugin.url_for(
        play_movie, movie_id=asset['id']), listitem)

@plugin.route('/channel/id=<channel_path>')
def show_channel(channel_path):
    current = 0
    #content = json.loads(get_url(ids.channel_url.format(channelpath=channel_path, offset=0), critical=True))
    content = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.channel_variables.format(channelpath=unquote(channel_path), offset=0),query = ids.channel_query), key = True, json = True, critical = True))
    if('data' in content and 'page' in content['data'] and 'assets' in content['data']['page']):
        add_from_fetch(content['data']['page']['assets'])
        while len(content['data']['page']['assets']) == ids.offset:
            #content = json.loads(get_url(ids.channel_url.format(channelpath=channel_path, offset=ids.offset*current), critical=True))
            content = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.channel_variables.format(channelpath=unquote(channel_path), offset=0),query = ids.channel_query), key = True, json = True, critical = True))
            if('data' in content and 'page' in content['data'] and 'assets' in content['data']['page']):
                add_from_fetch(content['data']['page']['assets'])
            else:
                break
            current += 1
    endOfDirectory(plugin.handle)

@plugin.route('/compilation/id=<compilation_id>')
def show_compilation(compilation_id):
    series_name = u''
    series_icon = u''
    series_poster = u''
    series_thumbnail = u''
    series_fanart = u''
    
    setContent(plugin.handle, 'tvshows')
    current = 0
    while True:
        content = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.compilation_items_variables.format(id = compilation_id, offset = ids.offset*current), query = ids.compilation_items_query), key = True, json = True, critical=True))
        #content = json.loads(post_url(ids.post_url, ids.compilation_items_post.format(id = compilation_id, offset = ids.offset*current), key = True, json = True, critical = True))
        if 'data' in content and content['data'] != None and 'compilation' in content['data'] and content['data']['compilation'] != None and 'compilationItems' in content['data']['compilation'] and content['data']['compilation']['compilationItems'] != None:
            for item in content['data']['compilation']['compilationItems']:
                if not series_name and 'compilation' in item:
                    series_name = item['compilation']['title']
                    for image in item['compilation']['images']:
                        if image['type'] == 'PRIMARY':
                            series_thumbnail = ids.image_url.format(image['url'])
                        elif image['type'] == 'ART_LOGO':
                            series_icon = ids.image_url.format(image['url'])
                        elif image['type'] == 'HERO_LANDSCAPE':
                            series_fanart = ids.image_url.format(image['url'])
                        elif image['type'] == 'HERO_PORTRAIT':
                            series_poster = ids.image_url.format(image['url'])
                airDATE = None
                toDATE = None
                airTIMES = u''
                endTIMES = u''
                Note_1 = u''
                Note_2 = u''
                if 'startsAt' in item and item['startsAt'] != None:
                    local_tz = tzlocal.get_localzone()
                    airDATES = datetime(1970, 1, 1) + timedelta(seconds=int(item['startsAt']))
                    airDATES = pytz.utc.localize(airDATES)
                    airDATES = airDATES.astimezone(local_tz)
                    airTIMES = airDATES.strftime('%d.%m.%Y - %H:%M')
                    airDATE = airDATES.strftime('%d.%m.%Y')
                
                if 'endsAt' in item and item['endsAt'] != None:
                    local_tz = tzlocal.get_localzone()
                    endDATES = datetime(1970, 1, 1) + timedelta(seconds=int(item['endsAt']))
                    endDATES = pytz.utc.localize(endDATES)
                    endDATES = endDATES.astimezone(local_tz)
                    endTIMES = endDATES.strftime('%d.%m.%Y - %H:%M')
                    toDATE =  endDATES.strftime('%d.%m.%Y')
                if airTIMES and endTIMES: 
                    Note_1 = kodiutils.get_string(32002).format(airTIMES, endTIMES)
                elif airTIMES: 
                    Note_1 = kodiutils.get_string(32017).format(airTIMES)
                elif endTIMES: 
                    Note_1 = kodiutils.get_string(32018).format(endTIMES)
                name = item['title']
                listitem = ListItem(name)
                # get images
                icon = u''
                poster = u''
                fanart = u''
                thumbnail = u''
                for image in item['images']:
                    if image['type'] == 'PRIMARY':
                        thumbnail = ids.image_url.format(image['url'])
                    elif image['type'] == 'ART_LOGO':
                        icon = ids.image_url.format(image['url'])
                    elif image['type'] == 'HERO_LANDSCAPE':
                        fanart = ids.image_url.format(image['url'])
                    elif image['type'] == 'HERO_PORTRAIT':
                        poster = ids.image_url.format(image['url'])
                if not poster:
                    poster = thumbnail
                if not fanart:
                    fanart = thumbnail
                if not icon:
                    icon = thumbnail
                listitem.setArt({'icon': icon, 'thumb': thumbnail, 'poster': poster, 'fanart': fanart})
                description = u''
                if 'description' in item and item['description'] != None:
                    description = item['description']
                age = u''
                if 'ageRating' in item and item['ageRating'] != None:
                    age = item['ageRating']['minAge']
                    if kodiutils.get_setting_as_bool('age_in_description'):
                        Note_2 += kodiutils.get_string(32037).format(age)
                if 'compilation' in item and item['compilation'] != None and 'copyrights' in item['compilation'] and item['compilation']['copyrights'] != None and len(item['compilation']['copyrights']) > 0:
                    if kodiutils.get_setting_as_bool('copyright_in_description'):
                        Note_2 += kodiutils.get_string(32038).format(', '.join(item['compilation']['copyrights']))
                if Note_2:
                    Note_2 = '[CR][CR]'+Note_2
                genres = []
                if 'genres' in item and item['genres'] != None:
                    for genre in item['genres']:
                        genres.append(genre['name'])
                listitem.setProperty('IsPlayable', 'true')
                listitem.setInfo(type='Video', infoLabels={'Title': name, 'Plot': Note_1+description+Note_2, 'Duration': item['video']['duration'], 'Date': airDATE, 'mpaa': age, 'genre': genres, 'mediatype': 'episode'})
                listitem.addContextMenuItems([('Queue', 'Action(Queue)')])
                addDirectoryItem(plugin.handle,plugin.url_for(
                    play_compilation_item, item_id=item['video']['id']), listitem)
            if len(content['data']['compilation']['compilationItems']) != ids.offset:
                break
        else:
            listitem = ListItem(kodiutils.get_string(32030))
            addDirectoryItem(plugin.handle, '', listitem, False)
            break
        current += 1
    add_favorites_folder(plugin.url_for(show_compilation, compilation_id),
        series_name, '', series_icon, series_poster, series_thumbnail, series_fanart)
    endOfDirectory(plugin.handle)

@plugin.route('/seasons/id=<show_id>')
def show_seasons(show_id):
    icon = u''
    poster = u''
    fanart = u''
    thumbnail = u''
    series_name = u''
    series_desc = u''
    #content_data = get_url(ids.series_url.format(seriesId = show_id), critical = False)
    content_data = post_url(ids.post_url, ids.post_request.format(variables=ids.series_variables.format(seriesId = show_id),query = ids.series_query), key = True, json = True, critical = True)
    if content_data:
        content = json.loads(content_data)
        if 'series' in content['data'] and content['data']['series'] != None:
            series_name = content['data']['series']['title']
            series_desc = content['data']['series']['description']
            Note_2 = u''
            if 'ageRating' in content['data']['series'] and content['data']['series']['ageRating'] != None:
                age = content['data']['series']['ageRating']['minAge']
                if kodiutils.get_setting_as_bool('age_in_description'):
                    Note_2 += kodiutils.get_string(32037).format(age)
            if 'copyrights' in content['data']['series'] and content['data']['series']['copyrights'] != None and len(content['data']['series']['copyrights']) > 0:
                if kodiutils.get_setting_as_bool('copyright_in_description'):
                    Note_2 += kodiutils.get_string(32038).format(', '.join(content['data']['series']['copyrights']))
            if Note_2:
                series_desc = series_desc + '[CR][CR]' + Note_2
            for image in content['data']['series']['images']:
                if image['type'] == 'PRIMARY':
                    thumbnail = ids.image_url.format(image['url'])
                elif image['type'] == 'ART_LOGO':
                    icon = ids.image_url.format(image['url'])
                elif image['type'] == 'HERO_LANDSCAPE':
                    fanart = ids.image_url.format(image['url'])
                elif image['type'] == 'HERO_PORTRAIT':
                    poster = ids.image_url.format(image['url'])
            if not poster and thumbnail:
                poster = thumbnail
            if not fanart and thumbnail:
                fanart = thumbnail
            if not icon and thumbnail:
                icon = thumbnail
            for season in content['data']['series']['seasons']:
                name = u'Staffel {0}'.format(season['number'])
                listitem = ListItem(name)
                # get images
                listitem.setArt({'icon': icon, 'thumb': thumbnail, 'poster': poster, 'fanart': fanart})
                listitem.setInfo(type='Video', infoLabels={'Title': name, 'Plot': series_desc, 'TvShowTitle': series_name})
                addDirectoryItem(plugin.handle,plugin.url_for(
                    show_season, season_id=season['id']), listitem, True)
            bonus_data = post_url(ids.post_url, ids.post_request.format(variables=ids.bonus_variables.format(seriesId = show_id, offset = 0),query = ids.bonus_query), key = True, json = True, critical = True)
            if bonus_data:
                bonus = json.loads(bonus_data)
                if 'series' in bonus['data'] and bonus['data']['series'] != None and 'extras' in bonus['data']['series'] and bonus['data']['series']['extras'] != None and len(bonus['data']['series']['extras']) > 0:
                    addDirectoryItem(plugin.handle,plugin.url_for(
                        show_bonus, id=show_id), ListItem(kodiutils.get_string(32036)), True)
            if kodiutils.get_setting_as_bool('show_recommendations'):
                addDirectoryItem(plugin.handle,plugin.url_for(
                    show_recommendations, id=show_id), ListItem(kodiutils.get_string(32035)), True)
        else:
            listitem = ListItem(kodiutils.get_string(32030))
            # get images
            addDirectoryItem(plugin.handle, '', listitem, False)
    add_favorites_folder(plugin.url_for(show_seasons, show_id),
        series_name, series_desc, icon, poster, thumbnail, fanart)
    endOfDirectory(plugin.handle)

@plugin.route('/season/id=<season_id>')
def show_season(season_id):
    setContent(plugin.handle, 'tvshows')
    current = 0
    while True:
        content = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.season_variables.format(seasonId = season_id, offset = ids.offset*current),query = ids.season_query), key = True, json = True, critical = True))
        for item in content['data']['season']['episodes']:
            airDATE = None
            toDATE = None
            airTIMES = u''
            endTIMES = u''
            Note_1 = u''
            Note_2 = u''
            if 'airdate' in item and item['airdate'] != None:
                local_tz = tzlocal.get_localzone()
                airDATES = datetime(1970, 1, 1) + timedelta(seconds=int(item['airdate']))
                airDATES = pytz.utc.localize(airDATES)
                airDATES = airDATES.astimezone(local_tz)
                airTIMES = airDATES.strftime('%d.%m.%Y - %H:%M')
                airDATE = airDATES.strftime('%d.%m.%Y')
            
            if 'endsAt' in item and item['endsAt'] != None:
                local_tz = tzlocal.get_localzone()
                endDATES = datetime(1970, 1, 1) + timedelta(seconds=int(item['endsAt']))
                endDATES = pytz.utc.localize(endDATES)
                endDATES = endDATES.astimezone(local_tz)
                endTIMES = endDATES.strftime('%d.%m.%Y - %H:%M')
                toDATE =  endDATES.strftime('%d.%m.%Y')
            if airTIMES and endTIMES: 
                Note_1 = kodiutils.get_string(32002).format(airTIMES, endTIMES)
            elif airTIMES: 
                Note_1 = kodiutils.get_string(32017).format(airTIMES)
            elif endTIMES: 
                Note_1 = kodiutils.get_string(32018).format(endTIMES)
            name = item['title']
            if kodiutils.get_setting_as_bool('number_in_name'):
                season = ''
                episode = ''
                if 'season' in item and 'number' in item['season'] and item['season']['number'] != None:
                    season = 'Staffel {0} '.format(item['season']['number'])
                if 'number' in item and item['number'] != None:
                    episode = 'Episode {0} '.format(item['number'])
                name = u'{0}{1}{2}'.format(season, episode, name)
            if len(item['licenseTypes']) == 1 and 'SVOD' in item['licenseTypes']:
                svod = kodiutils.get_setting_as_int('svod')
                if svod == 2:
                    return
                if svod == 0:
                    name = u'[PLUS+] ' + name
            age = u''
            if 'ageRating' in item and item['ageRating'] != None:
                age = item['ageRating']['minAge']
                if kodiutils.get_setting_as_bool('age_in_description'):
                    Note_2 += kodiutils.get_string(32037).format(age)
            if 'series' in item and item['series'] != None and 'copyrights' in item['series'] and item['series']['copyrights'] != None and len(item['series']['copyrights']) > 0:
                if kodiutils.get_setting_as_bool('copyright_in_description'):
                    Note_2 += kodiutils.get_string(32038).format(', '.join(item['series']['copyrights']))
            if Note_2:
                Note_2 = '[CR][CR]' + Note_2
            genres = []
            if 'genres' in item and item['genres'] != None:
                for genre in item['genres']:
                    genres.append(genre['name'])
            listitem = ListItem(name)
            # get images
            icon = u''
            poster = u''
            fanart = u''
            thumbnail = u''
            for image in item['images']:
                if image['type'] == 'PRIMARY':
                    thumbnail = ids.image_url.format(image['url'])
                elif image['type'] == 'ART_LOGO':
                    icon = ids.image_url.format(image['url'])
                elif image['type'] == 'HERO_LANDSCAPE':
                    fanart = ids.image_url.format(image['url'])
                elif image['type'] == 'HERO_PORTRAIT':
                    poster = ids.image_url.format(image['url'])
            if not poster:
                poster = thumbnail
            if not fanart:
                fanart = thumbnail
            if not icon:
                icon = thumbnail
            listitem.setArt({'icon': icon, 'thumb': thumbnail, 'poster': poster, 'fanart': fanart})
            description = item['description']
            listitem.setProperty('IsPlayable', 'true')
            listitem.setInfo(type='Video', infoLabels={'Title': name, 'Plot': Note_1+description+Note_2, 'Season': item['season']['number'], 'episode': item['number'], 'Duration': item['video']['duration'], 'Date': airDATE, 'mpaa': age, 'genre': genres, 'mediatype': 'episode'})
            listitem.addContextMenuItems([('Queue', 'Action(Queue)')])
            addDirectoryItem(plugin.handle,plugin.url_for(
                play_episode, episode_id=item['video']['id']), listitem)
        if len(content['data']['season']['episodes']) != ids.offset:
            break
        current += 1
    endOfDirectory(plugin.handle)

@plugin.route('/recommendations/id=<id>')
def show_recommendations(id):
    content_data = post_url(ids.post_url, ids.post_request.format(variables=ids.recommendation_variables.format(id = id),query = ids.recommendation_query), key = True, json = True, critical = True)
    if content_data:
        content = json.loads(content_data)
        if 'recommendationForAsset' in content['data'] and content['data']['recommendationForAsset'] != None:
            add_from_fetch(content['data']['recommendationForAsset']['assets'])
    endOfDirectory(plugin.handle)

@plugin.route('/bonus/id=<id>')
def show_bonus(id):
    offset = 0
    while True:
        content_data = post_url(ids.post_url, ids.post_request.format(variables=ids.bonus_variables.format(seriesId = id, offset = ids.offset*offset),query = ids.bonus_query), key = True, json = True, critical = True)
        if content_data:
            content = json.loads(content_data)
            if 'series' in content['data'] and content['data']['series'] != None and 'extras' in content['data']['series'] and content['data']['series']['extras'] != None:
                for item in content['data']['series']['extras']:
                    name = item['title']
                    listitem = ListItem(name)
                    # get images
                    icon = u''
                    poster = u''
                    fanart = u''
                    thumbnail = u''
                    for image in item['images']:
                        if image['type'] == 'PRIMARY':
                            thumbnail = ids.image_url.format(image['url'])
                        elif image['type'] == 'ART_LOGO':
                            icon = ids.image_url.format(image['url'])
                        elif image['type'] == 'HERO_LANDSCAPE':
                            fanart = ids.image_url.format(image['url'])
                        elif image['type'] == 'HERO_PORTRAIT':
                            poster = ids.image_url.format(image['url'])
                    if not poster:
                        poster = thumbnail
                    if not fanart:
                        fanart = thumbnail
                    if not icon:
                        icon = thumbnail
                    listitem.setArt({'icon': icon, 'thumb': thumbnail, 'poster': poster, 'fanart': fanart})
                    listitem.setProperty('IsPlayable', 'true')
                    listitem.setInfo(type='Video', infoLabels={'Title': name, 'Duration': item['video']['duration'], 'mediatype': 'episode'})
                    listitem.addContextMenuItems([('Queue', 'Action(Queue)')])
                    addDirectoryItem(plugin.handle,plugin.url_for(
                        play_episode, episode_id=item['video']['id']), listitem)
                if len(content['data']['series']['extras']) < ids.offset:
                    break
            else:
                break
    endOfDirectory(plugin.handle)

@plugin.route('/settings')
def open_settings():
    kodiutils.show_settings()

@plugin.route('/category/<category_id>')
def show_category(category_id):
    if category_id == 'favorites':
        xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_LABEL)
        global favorites
        if not favorites and xbmcvfs.exists(favorites_file_path):
            favorites_file = xbmcvfs.File(favorites_file_path)
            favorites = json.load(favorites_file)
            favorites_file.close()

        for item in favorites:
            listitem = ListItem(favorites[item]['name'])
            listitem.setArt({'icon': favorites[item]['icon'], 'thumb': favorites[item]['thumbnail'], 'poster': favorites[item]['poster'], 'fanart': favorites[item]['fanart']})
            listitem.setInfo('Video', {'plot': favorites[item]['desc']})
            add_favorites_context_menu(listitem, item, favorites[item]['name'], favorites[item]['desc'], favorites[item]['icon'], favorites[item]['poster'], favorites[item]['thumbnail'], favorites[item]['fanart'])
            addDirectoryItem(plugin.handle, url=item,
                listitem=listitem, isFolder=True)
    endOfDirectory(plugin.handle)

@plugin.route('/video/episode/<episode_id>')
def play_episode(episode_id):
    content = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.episode_variables.format(episodeId=episode_id),query = ids.episode_query), key = True, json = True, critical = True))
    content = content['data']['episode']
    play_video(episode_id, content['series']['id'], content['tracking']['brand'], content['video']['duration'])
    
@plugin.route('/video/compilation/<item_id>')
def play_compilation_item(item_id):
    content = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.compilation_item_variables.format(id=item_id),query = ids.compilation_item_query), key = True, json = True, critical = True))
    #content = json.loads(post_url(ids.post_url, ids.compilation_item_post.format(id=episode_id), key = True, json = True, critical = True))
    content = content['data']['compilationItem']
    play_video(item_id, content['compilation']['id'], content['tracking']['brand'], content['video']['duration'])
    
@plugin.route('/video/movie/<movie_id>')
def play_movie(movie_id):
    content = json.loads(post_url(ids.post_url, ids.post_request.format(variables=ids.movie_variables.format(id=movie_id),query = ids.movie_query), key = True, json = True, critical = True))
    #content = json.loads(post_url(ids.post_url, ids.compilation_item_post.format(id=episode_id), key = True, json = True, critical = True))
    content = content['data']['movie']
    play_video(content['video']['id'], content['id'], content['tracking']['brand'], content['video']['duration'])
    
def play_video(video_id, tvshow_id, brand, duration):
    if LooseVersion('18.0') > LooseVersion(xbmc.getInfoLabel('System.BuildVersion')):
        log(u'version is: {0}'.format(xbmc.getInfoLabel('System.BuildVersion')))
        kodiutils.notification(u'ERROR', kodiutils.get_string(32025))
        setResolvedUrl(plugin.handle, False, ListItem('none'))
        return
    player_config_data = json.loads(get_url(ids.player_config_url, key = False, cache = True, critical = True))
    player_config = json.loads(base64.b64decode(xxtea.decryptHexToStringss(player_config_data['toolkit']['psf'], ids.xxtea_key)))
    nuggvars_data = get_url(ids.nuggvars_url, key = False, critical = False)
    psf_config = json.loads(get_url(ids.psf_config_url, key = False, critical = True))
    playoutBaseUrl = psf_config['default']['vod']['playoutBaseUrl']
    entitlementBaseUrl = psf_config['default']['vod']['entitlementBaseUrl']

    postdata = u'{{"access_id":"{access_id}","content_id":"{content_id}","content_type":"VOD"}}'.format(access_id = player_config['accessId'], content_id = video_id)
    get_accesstoken()
    entitlement_headers = {ids.entitlement_token_header: ids.entitlement_token_header_format.format(token_type = kodiutils.get_setting('token_type'), token = kodiutils.get_setting('token'))}
    entitlement_headers['x-api-key'] = psf_config['default']['vod']['apiGatewayKey']
    entitlement_token_data = json.loads(post_url(entitlementBaseUrl+ids.entitlement_token_url, postdata = postdata, headers = entitlement_headers, json = True, critical = True, returnError=True))
    if 'error' in entitlement_token_data: #token to old get new one
        if entitlement_token_data['error'] == '401':
            get_accesstoken(True)
            entitlement_headers[ids.entitlement_token_header] = ids.entitlement_token_header_format.format(token_type = kodiutils.get_setting('token_type'), token = kodiutils.get_setting('token'))
            entitlement_token_data = json.loads(post_url(entitlementBaseUrl+ids.entitlement_token_url, postdata = postdata, headers = entitlement_headers, json = True, critical = True))
        else:
            if entitlement_token_data['error'] != '422':
                kodiutils.notification(u'ERROR', 'HTTP error {0}'.format(entitlement_token_data['error']))
            return

    nuggvars = nuggvars_data.replace('{"','').replace(',"url":""}','').replace('":','=').replace(',"','&')

    clientData = base64.b64encode((ids.clientdata.format(nuggvars=nuggvars[:-1], episode_id=video_id, duration=duration, brand=brand, tvshow_id=tvshow_id)).encode('utf-8')).decode('utf-8')
    log(u'clientData: {0}'.format(clientData))

    sig = u'{episode_id},{entitlement_token},{clientData}{xxtea_key_hex}'.format(episode_id=video_id, entitlement_token=entitlement_token_data['entitlement_token'], clientData=clientData, xxtea_key_hex=codecs.encode(ids.xxtea_key.encode('utf-8'),'hex').decode('utf-8'))
    sig = hashlib.sha1(sig.encode('UTF-8')).hexdigest()

    video_data_url = playoutBaseUrl+ids.video_playback_url.format(episode_id=video_id, entitlement_token=entitlement_token_data['entitlement_token'], clientData=clientData, sig=sig)

    playitem = ListItem()

    video_data = json.loads(post_url(video_data_url,postdata='server', critical=True))
    video_url = u''
    if 'vmap'in video_data and video_data['vmap']:
        #got add, extract mpd
        log(u'stream with add: {0}'.format(video_data['videoUrl']))
        video_url = video_data['videoUrl']
        video_url_data = get_url(video_url, headers={'User-Agent': ids.video_useragent}, key = False, critical = True)
        # get base url
        base_urls = re.findall('<BaseURL>(.*?)</BaseURL>',video_url_data)
        if len(base_urls) > 0 and base_urls[0].startswith('http'):
            video_url = base_urls[0] + u'.mpd|User-Agent='+ids.video_useragent
        else:
            kodiutils.notification(u'INFO', kodiutils.get_string(32005))
            setResolvedUrl(plugin.handle, False, playitem)
            return
    else:
        video_url = video_data['videoUrl'].rpartition('?')[0] + u'|User-Agent='+ids.video_useragent

    is_helper = None
    if video_data['drm'] != u'widevine':
        kodiutils.notification(u'ERROR', kodiutils.get_string(32004).format(video_data['drm']))
        return

    is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
    if not is_helper:
        setResolvedUrl(plugin.handle, False, playitem)
        return
    #check for inputstream_addon
    inputstream_installed = False
    inputstream_installed = is_helper._has_inputstream()

    if not inputstream_installed:
        # ask to install inputstream
        xbmc.executebuiltin('InstallAddon({})'.format(is_helper.inputstream_addon), True)
        inputstream_installed = is_helper._has_inputstream()

    if inputstream_installed and is_helper.check_inputstream():
        playitem.setPath(video_url)
        #playitem.path= = ListItem(label=xbmc.getInfoLabel('Container.ShowTitle'), path=urls["urls"]["dash"][drm_name]["url"]+"|User-Agent=vvs-native-android/1.0.10 (Linux;Android 7.1.1) ExoPlayerLib/2.8.1")
        log(u'video url: {0}'.format(video_url))
        log(u'licenseUrl: {0}'.format(video_data['licenseUrl']))
        playitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        playitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        playitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
        playitem.setProperty('inputstream.adaptive.license_key', video_data['licenseUrl'] +"|User-Agent="+ids.video_useragent+"&Content-Type=application/octet-stream|R{SSM}|")
        setResolvedUrl(plugin.handle, True, playitem)
    else:
        kodiutils.notification(u'ERROR', kodiutils.get_string(32019).format(drm))
        setResolvedUrl(plugin.handle, False, playitem)

@plugin.route('/live/<stream_id>/<brand>')
def play_live(stream_id, brand, _try=1):
    if LooseVersion('18.0') > LooseVersion(xbmc.getInfoLabel('System.BuildVersion')):
        log(u'version is: {0}'.format(xbmc.getInfoLabel('System.BuildVersion')))
        kodiutils.notification(u'ERROR', kodiutils.get_string(32025))
        setResolvedUrl(plugin.handle, False, ListItem('none'))
        return
    player_config_data = json.loads(get_url(ids.player_config_url, key = False, cache = True, critical = True))
    player_config = json.loads(base64.b64decode(xxtea.decryptHexToStringss(player_config_data['toolkit']['psf'], ids.xxtea_key)))
    psf_config = json.loads(get_url(ids.psf_config_url, key = False, critical = True))
    playoutBaseUrl = psf_config['default']['live']['playoutBaseUrl']
    entitlementBaseUrl = psf_config['default']['live']['entitlementBaseUrl']
    brand = html_parser.unescape(unquote(brand))
    #if sys.version_info[0] < 3:
    #    # decode utf-8
    #    brand = brand.decode('utf-8')

    postdata = u'{{"access_id":"{accessId}","content_id":"{stream_id}","content_type":"LIVE"}}'.format(accessId=player_config['accessId'], stream_id=stream_id)
    #'{"access_id":"'+ player_config['accessId']+'","content_id":"'+stream_id+'","content_type":"LIVE"}'
    get_accesstoken()
    entitlement_headers = {ids.entitlement_token_header: ids.entitlement_token_header_format.format(token_type = kodiutils.get_setting('token_type'), token = kodiutils.get_setting('token'))}
    entitlement_headers['x-api-key'] = psf_config['default']['vod']['apiGatewayKey']
    entitlement_token_data = json.loads(post_url(entitlementBaseUrl+ids.entitlement_token_url, postdata = postdata, headers = entitlement_headers, json = True, critical = True, returnError=True))
    if 'error' in entitlement_token_data: #token to old get new one
        if entitlement_token_data['error'] == '401':
            get_accesstoken(True)
            entitlement_headers[ids.entitlement_token_header] = ids.entitlement_token_header_format.format(token_type = kodiutils.get_setting('token_type'), token = kodiutils.get_setting('token'))
            entitlement_token_data = json.loads(post_url(entitlementBaseUrl+ids.entitlement_token_url, postdata = postdata, headers = entitlement_headers, json = True, critical = True))
        else:
            if entitlement_token_data['error'] != '422':
                kodiutils.notification(u'ERROR', 'HTTP error {0}'.format(entitlement_token_data['error']))
            return

    clientData = base64.b64encode((ids.clientdata_live.format(stream_id=stream_id, brand=brand)).encode('utf-8')).decode('utf-8')
    log(u'clientData: {0}'.format(clientData))

    sig = u'{stream_id},{entitlement_token},{clientData}{xxtea_key_hex}'.format(stream_id=stream_id, entitlement_token=entitlement_token_data['entitlement_token'], clientData=clientData, xxtea_key_hex=codecs.encode(ids.xxtea_key.encode('utf-8'),'hex').decode('utf-8'))
    #stream_id + ',' + entitlement_token_data['entitlement_token'] + ',' + clientData + codecs.encode(ids.xxtea_key.encode('utf-8'),'hex').decode('utf-8')
    sig = hashlib.sha1(sig.encode('UTF-8')).hexdigest()

    video_data_url = playoutBaseUrl+ids.live_playback_url.format(stream_id=stream_id, entitlement_token=entitlement_token_data['entitlement_token'], clientData=clientData, sig=sig)

    playitem = ListItem()

    video_data = json.loads(post_url(video_data_url, postdata='server', critical=True))

    is_helper = None
    if video_data['drm'] != 'widevine':
        kodiutils.notification('ERROR', kodiutils.get_string(32004).format(video_data['drm']))
        return
    
    video_url = video_data['videoUrl']
    video_url_data = u''
    if 'vmap'in video_data and video_data['vmap'] != None:
        #got add, extract mpd
        log(u'stream with add: {0}'.format(video_url))
        #return
        video_url_data = get_url(video_url, headers={'User-Agent': ids.video_useragent}, key = False, critical = True)
        if 'BaseURL' not in video_url_data and _try < kodiutils.get_setting_as_int('ad_tries'):
            log(u'No BaseURL in stream. try: {0}'.format(_try))
            play_live(stream_id, brand, _try+1)
            return
        if 'BaseURL' not in video_url_data:
            log(u'No BaseURL in stream. try limit of \'{0}\' reached. Show commercial timer'.format(kodiutils.get_setting_as_int('ad_tries')))
            success = False
            add_data = get_url(video_data['vmap'], headers={'User-Agent': ids.video_useragent}, key = False, critical = True)
            adds = re.findall('<Ad ((.|\n)*?)Ad>',add_data)
            number_of_adds = len(adds)
            duration = 0
            for add in adds:
                log(type(add))
                add_duration = re.findall('(?:yospace:AdBreak duration="|<Duration>)(.*?)(?:</Duration>|"/>)', add[0])
                duration += sum(time * int(milli) for time, milli in zip([3600000, 60000, 1000, 1], re.split('\D+', add_duration[0])))
            if duration > 0:
                if handle_wait(duration, number_of_adds, video_url, 5000):
                    video_url_data = get_url(video_url, headers={'User-Agent': ids.video_useragent}, key = False, critical = True)
                    success = 'BaseURL' in video_url_data
                    if not success:
                        if handle_wait_baseurl(kodiutils.get_setting_as_int('add_wait')*1000, 'title', 'text', video_url, 750):
                            video_url_data = get_url(video_url, headers={'User-Agent': ids.video_useragent}, key = False, critical = True)
                            success = 'BaseURL' in video_url_data
            if success == False:
                kodiutils.notification(u'ERROR', kodiutils.get_string(32005))
                setResolvedUrl(plugin.handle, False, ListItem('none'))
                return
    else:
        video_url_data = get_url(video_url, headers={'User-Agent': ids.video_useragent}, key = False, critical = True)
    
    # check base urls
    base_urls = re.findall('<BaseURL>(.*?)</BaseURL>', video_url_data)
    if len(base_urls) > 1:
        if base_urls[0].startswith('http'):
            video_url = base_urls[0] + base_urls[1] + u'cenc-default.mpd'

    log(u'video stream URL: {0}'.format(video_url))

    is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
    if not is_helper:
        setResolvedUrl(plugin.handle, False, playitem)
        return
    #check for inputstream_addon
    inputstream_installed = False
    inputstream_installed = is_helper._has_inputstream()

    if not inputstream_installed:
        # ask to install inputstream
        xbmc.executebuiltin('InstallAddon({})'.format(is_helper.inputstream_addon), True)
        inputstream_installed = is_helper._has_inputstream()

    if inputstream_installed and is_helper.check_inputstream():
        playitem.setPath(video_url + u'|User-Agent='+ids.video_useragent)
        #playitem.path= = ListItem(label=xbmc.getInfoLabel('Container.ShowTitle'), path=urls["urls"]["dash"][drm_name]["url"]+"|User-Agent=vvs-native-android/1.0.10 (Linux;Android 7.1.1) ExoPlayerLib/2.8.1")
        playitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        playitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        playitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
        playitem.setProperty("inputstream.adaptive.manifest_update_parameter", 'full')
        playitem.setProperty('inputstream.adaptive.license_key', video_data['licenseUrl'] + u'|User-Agent='+ids.video_useragent+'|R{SSM}|')
        setResolvedUrl(plugin.handle, True, playitem)
    else:
        kodiutils.notification(u'ERROR', kodiutils.get_string(32019).format(drm))
        setResolvedUrl(plugin.handle, False, playitem)

def utc_to_local(dt):
    if time.localtime().tm_isdst: return dt - timedelta(seconds=time.altzone)
    else: return dt - timedelta(seconds=time.timezone)

def add_favorites_folder(path, name, desc, icon, poster, thumbnail, fanart):
    global favorites
    if not favorites and xbmcvfs.exists(favorites_file_path):
        favorites_file = xbmcvfs.File(favorites_file_path)
        favorites = json.load(favorites_file)
        favorites_file.close()

    if not favorites or path not in favorites:
        # add favorites folder
        listitem = ListItem(kodiutils.get_string(32009))
        listitem.setArt({'icon': icon, 'thumb': thumbnail, 'poster': poster, 'fanart': fanart})
        addDirectoryItem(plugin.handle, url=plugin.url_for(add_favorite,
            path=quote(codecs.encode(path, 'UTF-8')), name=quote(codecs.encode(name, 'UTF-8')),
            desc=quote(codecs.encode(desc, 'UTF-8')), icon=quote(codecs.encode(icon, 'UTF-8')),
            poster=quote(codecs.encode(poster, 'UTF-8')), thumbnail=quote(codecs.encode(thumbnail, 'UTF-8')),
            fanart=quote(codecs.encode(fanart, 'UTF-8'))), listitem=listitem)
    else:
        # remove favorites
        listitem = ListItem(kodiutils.get_string(32010))
        listitem.setArt({'icon': icon, 'thumb': thumbnail, 'poster': poster, 'fanart': fanart})
        addDirectoryItem(plugin.handle, url=plugin.url_for(remove_favorite, query=quote(codecs.encode(path, 'UTF-8'))), listitem=listitem)

def add_favorites_context_menu(listitem, path, name, desc, icon, poster, thumbnail, fanart):
    global favorites
    if not favorites and xbmcvfs.exists(favorites_file_path):
        favorites_file = xbmcvfs.File(favorites_file_path)
        favorites = json.load(favorites_file)
        favorites_file.close()

    if not favorites or path not in favorites:
        # add favorites
        listitem.addContextMenuItems([(kodiutils.get_string(32009), 'RunScript('+ADDON.getAddonInfo('id')+
            ',add,' + quote(codecs.encode(path, 'UTF-8')) + ',' + quote(codecs.encode(name, 'UTF-8')) +
            ',' + quote(codecs.encode(desc, 'UTF-8')) + ',' + quote(codecs.encode(icon, 'UTF-8')) +
            ',' + quote(codecs.encode(poster, 'UTF-8')) + ',' + quote(codecs.encode(thumbnail, 'UTF-8')) +
            ',' + quote(codecs.encode(fanart, 'UTF-8')) + ')')])
    else:
        # remove favorites
        listitem.addContextMenuItems([(kodiutils.get_string(32010), 'RunScript('+ADDON.getAddonInfo('id') + ',remove,'+ quote(codecs.encode(path, 'UTF-8'))+')')])
    return listitem

@plugin.route('/add_fav')
def add_favorite():
    #data = plugin.args['query'][0].split('***')
    path = plugin.args['path'][0]
    name = plugin.args['name'][0]
    desc = ''
    icon = ''
    poster = ''
    thumbnail = ''
    fanart = ''
    if 'desc' in plugin.args:
        desc = plugin.args['desc'][0]
    if 'icon' in plugin.args:
        icon = plugin.args['icon'][0]
    if 'poster' in plugin.args:
        poster = plugin.args['poster'][0]
    if 'thumbnail' in plugin.args:
        thumbnail = plugin.args['thumbnail'][0]
    if 'fanart' in plugin.args:
        fanart = plugin.args['fanart'][0]
    
    if sys.version_info[0] < 3:
        # decode utf-8
        path = path.encode('ascii')
        name = name.encode('ascii')
        desc = desc.encode('ascii')
        icon = icon.encode('ascii')
        poster = poster.encode('ascii')
        thumbnail = thumbnail.encode('ascii')
        fanart = fanart.encode('ascii')
    
    path = unquote(path)
    name = unquote(name)
    desc = unquote(desc)
    icon = unquote(icon)
    poster = unquote(poster)
    thumbnail = unquote(thumbnail)
    fanart = unquote(fanart)
    
    if sys.version_info[0] < 3:
        # decode utf-8
        path = path.decode('utf-8')
        name = name.decode('utf-8')
        desc = desc.decode('utf-8')
        icon = icon.decode('utf-8')
        poster = poster.decode('utf-8')
        thumbnail = thumbnail.decode('utf-8')
        fanart = fanart.decode('utf-8')

    log(u'add favorite: {0}, {1}'.format(path, name))

    # load favorites
    global favorites
    if not favorites and xbmcvfs.exists(favorites_file_path):
        favorites_file = xbmcvfs.File(favorites_file_path)
        favorites = json.load(favorites_file)
        favorites_file.close()

    #favorites.update({data[0] : data[1]})
    favorites.update({path : {'name': name, 'desc': desc, 'icon': icon, 'poster': poster, 'thumbnail': thumbnail, 'fanart': fanart}})
    # load favorites
    favorites_file = xbmcvfs.File(favorites_file_path, 'w')
    json.dump(favorites, favorites_file, indent=2)
    favorites_file.close()

    # try:
    kodiutils.notification(kodiutils.get_string(32011), kodiutils.get_string(32012).format(name))
    # except UnicodeDecodeError:
    #     kodiutils.notification(kodiutils.get_string(32011), kodiutils.get_string(32012).format(name.decode('utf-8')))
    xbmc.executebuiltin('Container.Refresh')
    setResolvedUrl(plugin.handle, True, ListItem('none'))

@plugin.route('/remove_fav')
def remove_favorite():
    data = unquote(plugin.args['query'][0]).encode('utf-8').decode('utf-8')
    if sys.version_info[0] < 3:
        # decode utf-8
        data = data.decode('utf-8')
    log(u'remove favorite from folder: {0}'.format(data))
    # load favorites
    global favorites
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
    setResolvedUrl(plugin.handle, True, ListItem("none"))

def get_url(url, headers={}, key=True, cache=False, critical=False):
    log(u'get: {0}'.format(url))
    new_headers = {}
    new_headers.update({'User-Agent': ids.user_agent, 'Accept-Encoding': 'gzip'})
    if key:
        new_headers.update({'x-api-key': ids.middleware_token})
        new_headers.update({'Joyn-Platform': 'android'})
        new_headers.update({'Joyn-Client-Version': ids.joyn_version})
    new_headers.update(headers)
    if cache == True:
        new_headers.update({'If-Modified-Since': ids.get_config_tag(url)})
    try:
        request = urlopen(Request(url, headers=new_headers))
    except HTTPError as e:
        if cache and e.code == 304:
            return ids.get_config_cache(url)
        failure = str(e)
        if hasattr(e, 'code'):
            log(u'(getUrl) ERROR - ERROR - ERROR : ########## url:{0} === error:{1} === code:{2} ##########'.format(url, failure, e.code))
        elif hasattr(e, 'reason'):
            log(u'(getUrl) ERROR - ERROR - ERROR : ########## url:{0} === error:{1} === reason:{2} ##########'.format(url, failure, e.reason))
        try:
            data = u''
            if e.info().get('Content-Encoding') == 'gzip':
                # decompress content
                buffer = StringIO(e.read())
                deflatedContent = gzip.GzipFile(fileobj=buffer)
                data = deflatedContent.read()
            else:
                data = e.read()
            log(u'Error: ' + data.decode('utf-8'))
        except:
            log(u'couldn\'t read Error content')
            pass
        if critical:
            kodiutils.notification('ERROR GETTING URL', failure)
            return sys.exit(0)
        else:
            return u''
    except URLError as e:
        log(u'(getUrl) ERROR - ERROR - ERROR : ########## url:{0} === error:{1} === reason:{2} ##########'.format(url, str(e), e.reason))
        if critical:
            kodiutils.notification('ERROR GETTING URL', str(e))
            return sys.exit(0)
        else:
            return u''
    if request.info().get('Content-Encoding') == 'gzip':
        # decompress content
        buffer = StringIO(request.read())
        deflatedContent = gzip.GzipFile(fileobj=buffer)
        data = deflatedContent.read()
    else:
        data = request.read()
    data = data.decode('utf-8')
    if cache:
        ids.set_config_cache(url, data, request.info().get('Last-Modified'))
    return data

def post_url(url, postdata, headers={}, json = False, key = False, critical=False, returnError=False, proxy=False, newproxy=True):
    log(u'post: {0}, {1}'.format(url, headers))
    new_headers = {}
    new_headers.update(headers)
    new_headers.update({'User-Agent': ids.user_agent})
    if json:
        new_headers.update({'Content-Type': 'application/json; charset=utf-8'})
    if key:
        new_headers.update({'Accept-Encoding': 'gzip'})
        new_headers.update({'x-api-key': ids.middleware_token})
        new_headers.update({'Joyn-Platform': 'android'})
        #new_headers.update({'Joyn-Client-Version': ids.joyn_version})
    try:
        if proxy:
            if not check_proxy():
                kodiutils.notification(u'Proxy ERROR', 'no proxy found')
                return sys.exit(0)
            protocol_s = kodiutils.get_setting('current_proxy_protocol')
            ip = kodiutils.get_setting('current_proxy_ip')
            port = kodiutils.get_setting_as_int('current_proxy_port')
            timeout = kodiutils.get_setting_as_int('proxy_timeout')
            if protocol_s.lower() != 'http' and protocol_s.lower() != 'https':
                kodiutils.notification(u'Proxy ERROR', kodiutils.get_string(32043).format(protocol_s))
                return sys.exit(0)
            opener = build_opener(ProxyHandler({"https" : '{0}://{1}:{2}'.format(protocol_s, ip, port)}))
            try:
                request = opener.open(Request(url, headers=new_headers, data=postdata.encode('utf-8')), timeout=timeout)
            except URLError as e:
                log(u'(post_url) ERROR - proxy error: {0}'.format(e))
                if kodiutils.get_setting_as_bool('manual_proxy') or newproxy == False:
                    kodiutils.notification(u'ERROR GETTING URL', 'PROXY error')
                    if critical:
                        return sys.exit(0)
                    return u''
                #try another one
                if get_new_proxy():
                    return post_url(url, postdata, headers, json, key, critical, returnError, proxy, newproxy=False)
                kodiutils.notification(u'ERROR GETTING PROXY', kodiutils.get_string(32042))
                if critical:
                    return sys.exit(0)
        else:
            request = urlopen(Request(url, headers=new_headers, data=postdata.encode('utf-8')))
    except HTTPError as e:
        failure = str(e)
        if hasattr(e, 'code'):
            log(u'(post_url) ERROR - ERROR - ERROR : ########## {0} === {1} === {2} ##########'.format(url, postdata, failure))
        elif hasattr(e, 'reason'):
            log(u'(post_url) ERROR - ERROR - ERROR : ########## {0} === {1} === {2} ##########'.format(url, postdata, failure))
        data = u''
        try:
            if e.info().get('Content-Encoding') == 'gzip':
                # decompress content
                buffer = StringIO(e.read())
                deflatedContent = gzip.GzipFile(fileobj=buffer)
                data = deflatedContent.read()
            else:
                data = e.read()
            log(u'Error: {0}'.format(data.decode('utf-8')))
        except:
            log(u'couldn\'t read Error content')
            data = u''
            pass
        if critical:
            if hasattr(e, 'code') and getattr(e, 'code') == 422:
                if 'ENT_AssetNotAvailableInCountry' in data.decode('utf-8'):
                    kodiutils.notification(u'ERROR GETTING URL', kodiutils.get_string(32003))
                elif 'ENT_BusinessModelNotSuitable' in data:
                    kodiutils.notification(u'ERROR GETTING URL', kodiutils.get_string(32026))
                else:
                    kodiutils.notification(u'ERROR GETTING URL', kodiutils.get_string(32003))
            else:
                kodiutils.notification(u'ERROR GETTING URL', failure)
            if returnError:
                return u'{{"error": "{0}"}}'.format(getattr(e, 'code'))
            return sys.exit(0)
        else:
            if returnError:
                return u'{{"error": "{0}"}}'.format(getattr(e, 'code'))
            return u''

    if request.info().get('Content-Encoding') == 'gzip':
        # decompress content
        buffer = StringIO(request.read())
        deflatedContent = gzip.GzipFile(fileobj=buffer)
        data = deflatedContent.read()
    else:
        data = request.read()
    return data.decode('utf-8')

def handle_wait(time, commercials=1, url='', request_interval = 1000):
    log(u'waiting for {0} seconds'.format(time/1000.0))
    log(u'requesting url every {0} milliseconds'.format(request_interval))
    progress = xbmcgui.DialogProgress()
    text = kodiutils.get_string(32031).format(commercials)
    if commercials > 1:
        text = kodiutils.get_string(32041).format(commercials)
    progress.create(text)
    millisecs = 0
    percent = 0
    cancelled = False
    lasturl = 0
    while millisecs < time:
        percent = millisecs * 100 / time
        time_left = str((time - millisecs) / 1000.0)
        progress.update(percent, kodiutils.get_string(32032).format(seconds=time_left))
        if url != '' and lasturl + request_interval < millisecs:
            lasturl = millisecs
            get_url(url, headers={'User-Agent': ids.video_useragent}, key = False, critical = False)
        xbmc.sleep(100)
        millisecs += 100
        if (progress.iscanceled()):
            return False
    progress.close()
    return True

def handle_wait_baseurl(time, title, text, url, request_interval):
    log(u'waiting for baseurl')
    progress = xbmcgui.DialogProgress()
    progress.create(kodiutils.get_string(32039))
    millisecs = 0
    percent = 0
    finished = False
    lasturl = 0
    while not finished:
        percent = millisecs * 100 / time
        progress.update(percent, kodiutils.get_string(32040).format(seconds=millisecs/1000))
        if url != '' and lasturl + request_interval < millisecs:
            lasturl += request_interval
            video_url_data = get_url(url, headers={'User-Agent': ids.video_useragent}, key = False, critical = False)
            finished = 'BaseURL' in video_url_data
        xbmc.sleep(25)
        millisecs += 25
        if (progress.iscanceled()):
            return False
        if millisecs > time:
            video_url_data = get_url(url, headers={'User-Agent': ids.video_useragent}, key = False, critical = False)
            finished = 'BaseURL' in video_url_data
            break
    progress.close()
    return finished

def get_accesstoken(force = False):
    if kodiutils.get_setting('token_uuid') == '':
        kodiutils.set_setting('token_uuid', uuid.uuid4().hex)
    if (kodiutils.get_setting('token_time') != '' and not force) and not kodiutils.get_setting_as_bool('new_token'):
        log('checking old token')
        timestamp = int(kodiutils.get_setting('token_time'))
        if datetime.now() < datetime(1970, 1, 1) + timedelta(seconds=timestamp):
            log('old token still good')
            return
    log('requesting new token: force={0}'.format(force))
    kodiutils.set_setting('new_token', False)
    auth_key_url = ids.auth_key_url
    postdata = ids.auth_key_request.format(uuid_no_hyphen=kodiutils.get_setting('token_uuid'))
    headers = {'Accept-Encoding': 'gzip'}
    if kodiutils.get_setting_as_bool('use_proxy'):
        #headers['x-forwarded-for'] = u'53.{0}.{1}.{2}'.format(random.randint(0,256), random.randint(0,256), random.randint(0,256))
        token_data = json.loads(post_url(ids.auth_key_url, postdata, headers=headers, json = True, key = False, critical=True, proxy=True))
    else:
        token_data = json.loads(post_url(ids.auth_key_url, postdata, headers=headers, json = True, key = False, critical=True))
    log('token data: {0}'.format(token_data))
    kodiutils.set_setting('token_type', token_data['token_type'])
    kodiutils.set_setting('token', token_data['access_token'])
    valid = datetime.now() + timedelta(milliseconds=int(token_data['expires_in']))
    timestamp = int((valid - datetime(1970, 1, 1)).total_seconds())
    kodiutils.set_setting('token_time', timestamp)

def check_proxy():
    protocol = kodiutils.get_setting('current_proxy_protocol')
    ip = kodiutils.get_setting('current_proxy_ip')
    port = kodiutils.get_setting('current_proxy_port')
    if (protocol != '' and ip != '' and port != '' and test_proxy('{0}://{1}:{2}'.format(protocol, ip, port))) or kodiutils.get_setting_as_bool('manual_proxy'):
        return True
    return get_new_proxy()

def test_proxy(proxy):
    log('testing proxy: {0}'.format(proxy))
    timeout = kodiutils.get_setting_as_int('proxy_timeout')
    try:
        opener = build_opener(ProxyHandler({'http': proxy, 'https': proxy}))
        res = opener.open(Request('https://www.google.com'), timeout=timeout)
    except (HTTPError, Exception) as e:
        log('proxy is bad')
        return False
    log('proxy is good')
    return True

def get_new_proxy():
    protocol = kodiutils.get_setting('current_proxy_protocol')
    ip = kodiutils.get_setting('current_proxy_ip')
    port = kodiutils.get_setting('current_proxy_port')
    
    proxy_sites = kodiutils.get_setting('proxy_sites').split(';')
    proxy_sites = proxy_sites + ids.proxy_api_urls
    log('set proxy sites are: {0}'.format(proxy_sites))
    found_new = False
    progress = xbmcgui.DialogProgress()
    progress.create(kodiutils.get_string(32044))
    for site in proxy_sites:
        if site != '':
            if (progress.iscanceled()):
                return found_new
            sitetext = site[:int(site.find('/', 8))]
            log('checking "{0}" for proxies'.format(sitetext))
            progress.update(0, line1=kodiutils.get_string(32045).format(sitetext))
            data = get_url(site, key=False, critical=False)
            if data != '':
                newproxy = json.loads(data)
                if not 'data' in newproxy:
                    newproxy = {'data': [newproxy]}
                i = 0
                for proxy in newproxy['data']:
                    i += 1
                    if (progress.iscanceled()):
                        return found_new
                    if not 'error' in proxy:
                        progress.update(i*100/len(newproxy['data']), line1=kodiutils.get_string(32046).format(sitetext, '{0}://{1}:{2}'.format(proxy.get('type', proxy.get('protocol', proxy.get('proxyType'))), proxy['ip'], proxy['port']), i, len(newproxy['data'])))
                        if (proxy['ip'] != ip or proxy['port'] != port) and proxy['ip'] != '0.0.0.0':
                            if test_proxy('{0}://{1}:{2}'.format(proxy.get('type', proxy.get('protocol', proxy.get('proxyType'))), proxy['ip'], proxy['port'])):
                                found_new = True
                                protocol = kodiutils.set_setting('current_proxy_protocol', proxy.get('type', proxy.get('protocol', proxy.get('proxyType'))))
                                ip = kodiutils.set_setting('current_proxy_ip', proxy['ip'])
                                port = kodiutils.set_setting('current_proxy_port', proxy['port'])
                                progress.close()
                                return found_new
    progress.close()
    return found_new

def run():
    plugin.run()

def log(info):
    if kodiutils.get_setting_as_bool('debug') or xbmc.getCondVisibility('System.GetBool(debug.showloginfo)'):
        try:
            logger.warning(info)
        except UnicodeDecodeError:
            logger.warning(u'UnicodeDecodeError on logging')
            logger.warning(info.decode('utf-8'))
