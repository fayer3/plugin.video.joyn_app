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
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    from urllib.parse import quote, unquote
except ImportError:
    from urllib import quote, unquote
    from urllib2 import Request, urlopen, HTTPError

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
    content = json.loads(get_url(ids.overview_url, critical = True))
    for item in content['response']['blocks']:
        if item['type'] != 'ResumeLane' and 'items' in item:
            name = 'Folder'
            if 'Headline' in item['configuration']:
                name = item['configuration']['Headline']
            elif item['type'] == 'HeroLane':
                name = kodiutils.get_string(32001)
            if len(item['items']) > 1:
                addDirectoryItem(plugin.handle,plugin.url_for(
                    show_category, item['id']), ListItem(name), True)
            elif len(item['items']) == 1:
                cur = item['items'][0]
                query = []
                header = []
                for param in cur['fetch']['requiredParams']:
                    if param['in'] == 'query':
                        query.append(param['name'])
                    elif param['in'] == 'header':
                        header.append(param['name'])
                    else:
                        kodiutils.notification("ERROR", "new param location " + param['in'])
                        log("new param location " + param['in'])
                        log(json.dumps(param))
                addDirectoryItem(plugin.handle,plugin.url_for(
                    show_fetch, fetch_id=cur['fetch']['id'], type=cur['type'], query=quote(json.dumps(query)), header=quote(json.dumps(header))), ListItem(name), True)
                    #show_fetch, fetch_id=cur['fetch']['id'], query='&'.join(query), header='&'.join(header)), ListItem(name), True)
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
    query = query = xbmcgui.Dialog().input(kodiutils.get_string(32014))
    if query != '':
        content = json.loads(get_url(ids.search_tvshow_url.format(quote(query)), critical = True))
        add_series_from_fetch(content)
        #TODO check if this works search movies
        content = json.loads(get_url(ids.search_movie_url.format(quote(query)), critical = True))
        add_series_from_fetch(content)
    endOfDirectory(plugin.handle)

@plugin.route('/epg')
def show_epg():
    content = json.loads(get_url(ids.epg_now_url, critical = True))
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_LABEL)
    #log(json.dumps(content))
    for channel in content['response']['data']:
        listitem = get_epg_listitem(channel, channel_in_label = True)
        addDirectoryItem(plugin.handle,plugin.url_for(
            show_channel_epg, channel_id=channel['channelId']), listitem, True)
    endOfDirectory(plugin.handle)

@plugin.route('/epg/id=<channel_id>')
def show_channel_epg(channel_id):
    addDirectoryItem(plugin.handle,plugin.url_for(
        show_channel_epg_past, channel_id=channel_id), ListItem(kodiutils.get_string(32016)), True)
    dt_utcnow = datetime.utcnow().date()
    content = json.loads(get_url(ids.epg_channel_url.format(channel = channel_id)+'&from='+quote(dt_utcnow.strftime('%Y-%m-%d %H:%M:%S')), critical = True))
    #log(json.dumps(content))
    if len(content['response']['data']) > 0:
        date_max = datetime.fromtimestamp(content['response']['data'][len(content['response']['data'])-1]['startTime'])
        for n in range(int ((date_max.date() - dt_utcnow).days+1)):
            cur_date = (dt_utcnow + timedelta(days=n))
            addDirectoryItem(plugin.handle,plugin.url_for(
                show_channel_epg_date, channel_id=channel_id, day=cur_date.day, month=cur_date.month, year=cur_date.year), ListItem(kodiutils.get_string(32015).format(cur_date.strftime('%Y-%m-%d'))), True)

    endOfDirectory(plugin.handle)

@plugin.route('/epg/id=<channel_id>/past')
def show_channel_epg_past(channel_id):
    dt_utcnow = datetime.utcnow().date()
    content = json.loads(get_url(ids.epg_channel_url.format(channel = channel_id)+'&to='+quote(dt_utcnow.strftime('%Y-%m-%d %H:%M:%S')), critical = True))
    #log(json.dumps(content))
    if len(content['response']['data']) > 0:
        date_min = datetime.fromtimestamp(content['response']['data'][0]['startTime'])
        for n in range(int ((dt_utcnow - date_min.date()).days)):
            cur_date = (dt_utcnow - timedelta(days=n))
            addDirectoryItem(plugin.handle,plugin.url_for(
                show_channel_epg_date, channel_id=channel_id, day=cur_date.day, month=cur_date.month, year=cur_date.year), ListItem(kodiutils.get_string(32015).format(cur_date.strftime('%Y-%m-%d'))), True)
    endOfDirectory(plugin.handle)

@plugin.route('/epg/id=<channel_id>/day=<day>/month=<month>/year=<year>')
def show_channel_epg_date(channel_id, day, month, year):
    log('EPG for channel "{0}" and date "{1}.{2}.{3}"'.format(channel_id, day, month, year))

    cur_date = date(int(year), int(month), int(day))

    content = json.loads(get_url(ids.epg_channel_url.format(channel = channel_id)+'&from='+quote(cur_date.strftime('%Y-%m-%d %H:%M:%S'))+'&to='+quote((cur_date+timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')), critical = True))
    for channel in content['response']['data']:
        listitem = get_epg_listitem(channel, start_in_label = True)
        addDirectoryItem(plugin.handle, plugin.url_for(show_info), listitem)
    endOfDirectory(plugin.handle)

def get_epg_listitem(channeldata, channel_in_label = False, start_in_label = False):
    infoLabels = {}
    art = {}
    infoLabels.update({'title': channeldata['title'] if channeldata['title'] else channeldata['tvShow']['title']})
    infoLabels.update({'tvShowTitle': channeldata['tvShow']['title']})
    infoLabels.update({'year': channeldata['productionYear']})
    channelname =  channeldata['tvChannelName']

    local_start_time = datetime.fromtimestamp(channeldata['startTime'])
    local_end_time = datetime.fromtimestamp(channeldata['endTime'])
    plot = u'[COLOR chartreuse]{0} - {1}[/COLOR]'.format(local_start_time.strftime('%H:%M'), local_end_time.strftime('%H:%M'))
    plot += u'[CR][CR]'
    plot = plot + channeldata['description'] if channeldata['description'] else u''
    infoLabels.update({'plot': plot})

    genres = []
    for genre in channeldata['genres']:
        #log('genre: {0}'.format(genre))
        #log('genres: {0}'.format(genres))
        if genre['title'] and genre['title'] not in genres:
            genres.append(genre['title'])
    if len(genres) > 0:
        infoLabels.update({'genre': ', '.join(genres)})

    if len(channeldata['images']) > 0:
        for image in channeldata['images']:
            if image['subType'] == 'art_direction' or image['subType'] == 'logo':
                art.update({'fanart': ids.image_url.format(image['url'])})
            elif image['subType'] == 'cover':
                art.update({'thumb': ids.image_url.format(image['url'])})

    infoLabels.update({'mediatype': 'episode'})

    label = u''
    if channel_in_label:
        if channelname != infoLabels.get('tvShowTitle'):
            label = infoLabels.get('tvShowTitle') if not infoLabels.get('title') or infoLabels.get('tvShowTitle') == infoLabels.get('title') else u'[COLOR blue]{0}[/COLOR]  {1}'.format(infoLabels.get('tvShowTitle'), infoLabels.get('title'))
            label = u'[COLOR lime]{0}[/COLOR]  {1}'.format(channelname, label)
            if kodiutils.get_setting_as_bool('channel_name_in_stream_title'):
                infoLabels['title'] = label
        else:
            label = channelname
    else:
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
    query = json.loads(unquote(plugin.args['query'][0]))
    header = json.loads(unquote(plugin.args['header'][0]))
    content = fetch(fetch_id, query, header)
    add_from_fetch(content, type)
    endOfDirectory(plugin.handle)

def fetch(fetch_id, query, header):
    url = ids.fetch_url.format(fetch_id)
    url += u'?'
    if query:
        for q in query:
            if q == 'selection':
                url += ids.fetch_selection
            else:
                kodiutils.notification("ERROR", "unknown query parameter: " + q)
                log("unknown query parameter: " + q)
    headers = {}
    if header:
        for h in header:
            if h != 'key':
                kodiutils.notification("ERROR", "unknown header parameter: " + h)
                log("unknown header parameter: " + h)
    content = json.loads(get_url(url, headers = headers, critical=True))
    return content

def add_from_fetch(content, type):
    if type.lower() == 'series':
        add_series_from_fetch(content)
    elif type.lower() == 'tvchannel':
        add_tvchannel_from_fetch(content)
    elif type.lower() == 'query':
        add_livestreams()
    else:
        kodiutils.notification("ERROR", "unkown type " + type)
        log("unkown type " + type)
        log(json.dumps(param))

def add_series_from_fetch(content):
    for item in content['response']['data']:
        name = ''
        for title in item['metadata']['de']['titles']:
            if title['type'] == 'main':
                name = title['text']
        listitem = ListItem(name)
        # get images
        icon=''
        poster = ''
        fanart = ''
        thumbnail = ''
        for image in item['metadata']['de']['images']:
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
        listitem.setArt({'icon': icon, 'thumb': thumbnail, 'poster': poster, 'fanart': fanart})
        description = ''
        for desc in item['metadata']['de']['descriptions']:
            if desc['type'] == 'main':
                description = desc['text']
        listitem.setInfo(type='Video', infoLabels={'Title': name, 'Plot': description, 'TvShowTitle': name})
        add_favorites_context_menu(listitem, plugin.url_for(
            show_seasons, show_id=item['id']), name, description, icon, poster, thumbnail, fanart)
        addDirectoryItem(plugin.handle, plugin.url_for(
            show_seasons, show_id=item['id']), listitem, True)

def add_tvchannel_from_fetch(content):
    #log(json.dumps(content))
    for item in content['response']['data']:
        name = ''
        for title in item['metadata']['de']['titles']:
            if title['type'] == 'main':
                name = title['text']
        listitem = ListItem(name)
        # get images
        icon=''
        for image in item['metadata']['de']['images']:
            if image['type'] == 'BRAND_LOGO':
                icon = ids.image_url.format(image['url'])
        listitem.setArt({'icon': icon, 'thumb': icon, 'poster': icon})
        description = ''
        for desc in item['metadata']['de']['descriptions']:
            if desc['type'] == 'seo':
                description = desc['text']
        listitem.setInfo(type='Video', infoLabels={'Title': name, 'Plot': description, 'TvShowTitle': name})
        addDirectoryItem(plugin.handle,plugin.url_for(
            show_channel, channel_id=item['channelId']), listitem, True)

def add_livestreams():

    livestreams = []
    dt_utcnow = datetime.utcnow().replace(second=0)
    dt_from = dt_utcnow - timedelta(hours=4)
    dt_to = dt_utcnow + timedelta(hours=10)
    epg_content = json.loads(get_url(ids.epg_url.format(quote(dt_from.strftime('%Y-%m-%d %H:%M:%S')), quote(dt_to.strftime('%Y-%m-%d %H:%M:%S'))), critical=True))

    content = json.loads(get_url(ids.livestream_url, critical=True))
    for item in content['response']['data']:
        dt_now = datetime.now()
        epg_now = None
        epg_next = None
        for epg in epg_content['response']['data']:
            if epg['channelId'] == item['channelId']:
                if datetime.fromtimestamp(epg['startTime']) < dt_now and dt_now < datetime.fromtimestamp(epg['endTime']):
                    epg_now = epg
                elif datetime.fromtimestamp(epg['startTime']) > dt_now:
                    epg_next = epg
                if epg_now and epg_next:
                    break

        brand = u''
        infoLabels = {}
        art = {}
        if epg_now:
            brand = epg_now['tvChannelName']
            infoLabels.update({'title': epg_now['title'] if epg_now['title'] else epg_now['tvShow']['title']})
            infoLabels.update({'tvShowTitle': epg_now['tvShow']['title']})
            infoLabels.update({'year': epg_now['productionYear']})

            local_start_time = datetime.fromtimestamp(epg_now['startTime'])
            local_end_time = datetime.fromtimestamp(epg_now['endTime'])
            plot = '{0} - {1}'.format(local_start_time.strftime('%H:%M'), local_end_time.strftime('%H:%M'))
            if epg_next:
                next_title = epg_next.get('title') if epg_next.get('title') else None
                next_show = epg_next.get('tvShow').get('title') if epg_next.get('tvShow') else u''

                plot += u'[CR]{0}: [COLOR blue]{1}[/COLOR] {2}'.format(kodiutils.get_string(32006), next_show, next_title) if next_title and next_show != u'' and next_title != next_show else u'[CR]{0}: {1}'.format(kodiutils.get_string(32006),next_title if next_title else next_show)

            plot += u'[CR][CR]'
            plot += epg_now['description'] if epg_now['description'] else u''
            infoLabels.update({'plot': plot})

            genres = []
            for genre in epg_now['genres']:
                if genre['title'] not in genres:
                    genres.append(genre['title'])
            if len(genres) > 0:
                infoLabels.update({'genre': u', '.join(genres)})

            for image in item['metadata']['de']['images']:
                if image['type'] == 'BRAND_LOGO':
                    icon = ids.image_url.format(image['url'])
                    art.update({'icon': icon, 'thumb': icon})
            if len(epg_now['images']) > 0 and kodiutils.get_setting_as_bool('live_preview_for_icon'):
                for image in epg_now['images']:
                    if image['subType'] == 'art_direction':
                        art.update({'fanart': ids.image_url.format(image['url'])})
                    elif image['subType'] == 'cover':
                        art.update({'thumb': ids.image_url.format(image['url'])})
        else:
            for title in item['metadata']['de']['titles']:
                if title['type'] == 'main':
                    brand = title['text']
                    infoLabels.update({'title': brand})
                    infoLabels.update({'tvShowTitle': brand})

            # get images
            for image in item['metadata']['de']['images']:
                if image['type'] == 'BRAND_LOGO':
                    icon = ids.image_url.format(image['url'])
                    art.update({'icon': icon, 'thumb': icon, 'poster': icon})

            for desc in item['metadata']['de']['descriptions']:
                if desc['type'] == 'main':
                    infoLabels.update({'plot': desc['text']})

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
        if len(item['metadata']['de']['livestreams']) > 0:
            livestreams.append((plugin.url_for(
                play_live, stream_id=item['metadata']['de']['livestreams'][0]['streamId'], brand=quote(brand.encode('ascii', 'xmlcharrefreplace'))), listitem))

    livestreams.sort(key=lambda x: x[1].getLabel().lower(), reverse=False)

    addDirectoryItems(plugin.handle, livestreams)


@plugin.route('/channel/id=<channel_id>')
def show_channel(channel_id):
    current = 0
    content = json.loads(get_url(ids.channel_url.format(current, channel_id), critical=True))
    add_series_from_fetch(content)
    while len(content['response']['data']) == ids.channel_limit:
        current += ids.channel_limit
        content = json.loads(get_url(ids.channel_url.format(current, channel_id), critical=True))
        add_series_from_fetch(content)
    endOfDirectory(plugin.handle)

@plugin.route('/seasons/id=<show_id>')
def show_seasons(show_id):

    icon = u''
    poster = u''
    fanart = u''
    thumbnail = u''
    series_name = u''
    series_desc = u''
    content_tvshow_data = get_url(ids.tvshow_url.format(show_id), critical = False)
    if content_tvshow_data:
        content_tvshow = json.loads(content_tvshow_data)
        for item in content_tvshow['response']['data']:
            for title in item['metadata']['de']['titles']:
                if title['type'] == 'main':
                    series_name = title['text']
                    break
            for desc in item['metadata']['de']['descriptions']:
                if desc['type'] == 'main':
                    series_desc = desc['text']
                    break
            if series_name != '' and series_desc != '':
                break

        for image in content_tvshow['response']['data'][0]['metadata']['de']['images']:
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
    content_data = get_url(ids.seasons_url.format(show_id), critical = False)
    if content_data:
        content = json.loads(content_data)
        for item in content['response']['data']:
            name = u''
            if 'seasonNumber' in str(item['metadata']['de']) and str(item['metadata']['de']['seasonNumber']) != '':
                name = u'Staffel {0}'.format(item['metadata']['de']['seasonNumber'])
            else:
                for title in item['metadata']['de']['titles']:
                    if title['type'] == 'main':
                        name = title['text']
            listitem = ListItem(name)
            # get images
            icon = u''
            for image in item['metadata']['de']['images']:
                if image['type'] == 'PRIMARY':
                    icon = ids.image_url.format(image['url'])
            listitem.setArt({'icon': icon, 'thumb': thumbnail, 'poster': poster, 'fanart': fanart})
            description = u''
            for desc in item['metadata']['de']['descriptions']:
                if desc['type'] == 'main':
                    description = desc['text']
            listitem.setInfo(type='Video', infoLabels={'Title': name, 'Plot': description, 'TvShowTitle': name})
            addDirectoryItem(plugin.handle,plugin.url_for(
                show_season, season_id=item['id']), listitem, True)
    add_favorites_folder(plugin.url_for(show_seasons, show_id),
        series_name, series_desc, icon, poster, thumbnail, fanart)
    endOfDirectory(plugin.handle)

@plugin.route('/season/id=<season_id>')
def show_season(season_id):
    setContent(plugin.handle, 'tvshows')
    content = json.loads(get_url(ids.season_url.format(season_id), critical = True))
    for item in content['response']['data']:
        goDATE = None
        toDATE = None
        startTIMES = u''
        endTIMES = u''
        Note_1 = u''
        if 'visibilities' in item:
            local_tz = tzlocal.get_localzone()
            startDATES = datetime(1970, 1, 1) + timedelta(seconds=int(item['visibilities'][0]['startsAt']))
            log('offset: {0}'.format(startDATES.utcoffset()))
            startTIMES = startDATES.strftime('%d.%m.%Y - %H:%M')
            goDATE =  startDATES.strftime('%d.%m.%Y')
            endDATES = datetime(1970, 1, 1) + timedelta(seconds=int(item['visibilities'][0]['endsAt']))
            endDATES = pytz.utc.localize(endDATES)
            endDATES = endDATES.astimezone(local_tz)
            endTIMES = endDATES.strftime('%d.%m.%Y - %H:%M')
            toDATE =  endDATES.strftime('%d.%m.%Y')
        if startTIMES and endTIMES: Note_1 = kodiutils.get_string(32002).format(startTIMES, endTIMES)
        name = u''
        for title in item['metadata']['de']['titles']:
            if title['type'] == 'main':
                name = title['text']
        if kodiutils.get_setting_as_bool('number_in_name'):
            season = ''
            episode = ''
            if 'seasonNumber' in item['metadata']['de'] and item['metadata']['de']['seasonNumber'] != None:
                season = 'Staffel {0} '.format(item['metadata']['de']['seasonNumber'])
            if 'episodeNumber' in item['metadata']['de'] and item['metadata']['de']['episodeNumber'] != None:
                episode = 'Episode {0} '.format(item['metadata']['de']['episodeNumber'])
            name = u'{0}{1}{2}'.format(season, episode, name)
        listitem = ListItem(name)
        # get images
        icon = u''
        poster = u''
        fanart = u''
        thumbnail = u''
        for image in item['metadata']['de']['images']:
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
        for desc in item['metadata']['de']['descriptions']:
            if desc['type'] == 'main':
                description = desc['text']
        listitem.setProperty('IsPlayable', 'true')
        listitem.setInfo(type='Video', infoLabels={'Title': name, 'Plot': Note_1+description, 'TvShowTitle': html_parser.unescape(item['tvShow']['titles']['default']), 'Season': item['metadata']['de']['seasonNumber'], 'episode': item['metadata']['de']['episodeNumber'], 'Duration': item['metadata']['de']['video']['duration'], 'Date': goDATE, 'mediatype': 'episode'})
        listitem.addContextMenuItems([('Queue', 'Action(Queue)')])
        addDirectoryItem(plugin.handle,plugin.url_for(
            play_episode, episode_id=item['id']), listitem)
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
    else:
        content = json.loads(get_url(ids.overview_url, critical = True))
        for category in content['response']['blocks']:
            if category_id == category['id']:
                if multiprocess:
                    threads = []
                    pool = ThreadPool(processes=kodiutils.get_setting_as_int('simultanious_requests'))
                for item in category['items']:
                    query = []
                    header = []
                    for param in item['fetch']['requiredParams']:
                        if param['in'] == 'query':
                            query.append(param['name'])
                        elif param['in'] == 'header':
                            header.append(param['name'])
                        else:
                            kodiutils.notification(u'ERROR', u'new param location {0}'.format(param['in']))
                            log(u'new param location {0}'.format(param['in']))
                            log(json.dumps(param))
                    #fetch(fetch_id=item['fetch']['id'], query=query, header=header)
                    if multiprocess:
                        thread = pool.apply_async(fetch, (item['fetch']['id'], query, header))
                        thread.name = item['type']
                        thread.daemon = True
                        threads.append(thread)
                    else:
                        add_from_fetch(fetch(item['fetch']['id'], query, header), item['type'])
                if multiprocess:
                    for thread in threads:
                        add_from_fetch(thread.get(), thread.name)
                        pool.close()
                        pool.join()
    endOfDirectory(plugin.handle)

@plugin.route('/episode/<episode_id>')
def play_episode(episode_id):
    if LooseVersion('18.0') > LooseVersion(xbmc.getInfoLabel('System.BuildVersion')):
        log(u'version is: {0}'.format(xbmc.getInfoLabel('System.BuildVersion')))
        kodiutils.notification(u'ERROR', kodiutils.get_string(32025))
        setResolvedUrl(plugin.handle, False, ListItem('none'))
        return
    content = json.loads(get_url(ids.video_info_url.format(episode_id), critical = True))
    player_config_data = json.loads(get_url(ids.player_config_url, cache = True, critical = True))
    player_config = json.loads(base64.b64decode(xxtea.decryptHexToStringss(player_config_data['toolkit']['psf'], ids.xxtea_key)))
    nuggvars_data = get_url(ids.nuggvars_url, critical=True)
    psf_config = json.loads(get_url(ids.psf_config_url, critical = True))
    playoutBaseUrl = psf_config['default']['vod']['playoutBaseUrl']
    entitlementBaseUrl = psf_config['default']['vod']['entitlementBaseUrl']

    postdata = u'{{"access_id":"{access_id}","content_id":"{content_id}","content_type":"VOD"}}'.format(access_id = player_config['accessId'], content_id = episode_id)
    if kodiutils.get_setting_as_bool('fake_ip'):
        entitlement_token_data = json.loads(post_url(entitlementBaseUrl+ids.entitlement_token_url, postdata=postdata, headers={'x-api-key': psf_config['default']['vod']['apiGatewayKey'], u'x-forwarded-for': u'53.{0}.{1}.{2}'.format(random.randint(0,256), random.randint(0,256), random.randint(0,256))}, json = True, critical=True))
    else:
        entitlement_token_data = json.loads(post_url(entitlementBaseUrl+ids.entitlement_token_url, postdata=postdata, headers={u'x-api-key': psf_config['default']['vod']['apiGatewayKey']}, json = True, critical=True))

    tracking = content['response']['tracking']
    genres = u'["'+u'","'.join(tracking['genres'])+u'"]'

    nuggvars = nuggvars_data.replace('{"','').replace(',"url":""}','').replace('":','=').replace(',"','&')

    clientData = base64.b64encode((ids.clientdata.format(nuggvars=nuggvars[:-1], episode_id=episode_id, duration=content['response']['video']['duration'], brand=tracking['channel'], genres=genres, tvshow_id=tracking['tvShow']['id'])).encode('utf-8')).decode('utf-8')
    log(u'clientData: {0}'.format(clientData))

    sig = u'{episode_id},{entitlement_token},{clientData}{xxtea_key_hex}'.format(episode_id=episode_id, entitlement_token=entitlement_token_data['entitlement_token'], clientData=clientData, xxtea_key_hex=codecs.encode(ids.xxtea_key.encode('utf-8'),'hex').decode('utf-8'))
    sig = hashlib.sha1(sig.encode('UTF-8')).hexdigest()

    video_data_url = playoutBaseUrl+ids.video_playback_url.format(episode_id=episode_id, entitlement_token=entitlement_token_data['entitlement_token'], clientData=clientData, sig=sig)

    playitem = ListItem()

    video_data = json.loads(post_url(video_data_url,postdata='server', critical=True))
    video_url = u''
    if 'vmap'in video_data and video_data['vmap']:
        #got add, extract mpd
        log(u'stream with add: {0}'.format(video_data['videoUrl']))
        video_url = video_data['videoUrl']
        video_url_data = get_url(video_url, critical = True)
        # get base url
        base_urls = re.findall('<BaseURL>(.*?)</BaseURL>',video_url_data)
        if len(base_urls) > 0 and base_urls[0].startswith('http'):
            video_url = base_urls[0] + u'.mpd|User-Agent=vvs-native-android/3.1.0.301003151 (Linux;Android 7.1.1) ExoPlayerLib/2.10.0'
        else:
            kodiutils.notification(u'INFO', kodiutils.get_string(32005))
            setResolvedUrl(plugin.handle, False, playitem)
            return
    else:
        video_url = video_data['videoUrl'].rpartition('?')[0] + u'|User-Agent=vvs-native-android/3.1.0.301003151 (Linux;Android 7.1.1) ExoPlayerLib/2.10.0'

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
        playitem.setProperty('inputstream.adaptive.license_key', video_data['licenseUrl'] +"|User-Agent=vvs-native-android/3.1.0.301003151 (Linux;Android 7.1.1) ExoPlayerLib/2.10.0&Content-Type=application/octet-stream|R{SSM}|")
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
    player_config_data = json.loads(get_url(ids.player_config_url, cache = True, critical = True))
    player_config = json.loads(base64.b64decode(xxtea.decryptHexToStringss(player_config_data['toolkit']['psf'], ids.xxtea_key)))
    psf_config = json.loads(get_url(ids.psf_config_url, critical = True))
    playoutBaseUrl = psf_config['default']['live']['playoutBaseUrl']
    entitlementBaseUrl = psf_config['default']['live']['entitlementBaseUrl']
    brand = html_parser.unescape(unquote(brand))
    #if sys.version_info[0] < 3:
    #    # decode utf-8
    #    brand = brand.decode('utf-8')

    postdata = u'{{"access_id":"{accessId}","content_id":"{stream_id}","content_type":"LIVE"}}'.format(accessId=player_config['accessId'], stream_id=stream_id)
    #'{"access_id":"'+ player_config['accessId']+'","content_id":"'+stream_id+'","content_type":"LIVE"}'
    if kodiutils.get_setting_as_bool('fake_ip'):
        entitlement_token_data = json.loads(post_url(entitlementBaseUrl+ids.entitlement_token_url, postdata=postdata, headers={'x-api-key': psf_config['default']['live']['apiGatewayKey'], u'x-forwarded-for': u'53.{0}.{1}.{2}'.format(random.randint(0,256), random.randint(0,256), random.randint(0,256))}, json = True, critical=True))
    else:
        entitlement_token_data = json.loads(post_url(entitlementBaseUrl+ids.entitlement_token_url, postdata=postdata, headers={u'x-api-key': psf_config['default']['live']['apiGatewayKey']}, json = True, critical=True))

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
    if 'vmap'in video_data and video_data['vmap']:
        #got add, extract mpd
        log(u'stream with add: {0}'.format(video_url))
        #return
        video_url_data = get_url(video_url, headers={'User-Agent': 'vvs-native-android/3.1.0.301003151 (Linux;Android 7.1.1) ExoPlayerLib/2.10.0'}, key = False, critical = True)
        if 'BaseURL' not in video_url_data and _try < kodiutils.get_setting_as_int('ad_tries'):
            play_live(stream_id, brand, _try+1)
            return
        if 'BaseURL' not in video_url_data:
            kodiutils.notification(u'ERROR', kodiutils.get_string(32005))
            setResolvedUrl(plugin.handle, False, ListItem('none'))
            return
    else:
        video_url_data = get_url(video_url, critical = True)
    
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
        playitem.setPath(video_url + u'|User-Agent=vvs-native-android/3.1.0.301003151 (Linux;Android 7.1.1) ExoPlayerLib/2.10.0')
        #playitem.path= = ListItem(label=xbmc.getInfoLabel('Container.ShowTitle'), path=urls["urls"]["dash"][drm_name]["url"]+"|User-Agent=vvs-native-android/1.0.10 (Linux;Android 7.1.1) ExoPlayerLib/2.8.1")
        playitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        playitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        playitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
        playitem.setProperty("inputstream.adaptive.manifest_update_parameter", 'full')
        playitem.setProperty('inputstream.adaptive.license_key', video_data['licenseUrl'] + u'|User-Agent=vvs-native-android/3.1.0.301003151 (Linux;Android 7.1.1) ExoPlayerLib/2.10.0|R{SSM}|')
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
        new_headers.update({'key': ids.middleware_token})
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
            log(u'(getUrl) ERROR - ERROR - ERROR : ########## {0} === {1} ##########'.format(url, failure))
        elif hasattr(e, 'reason'):
            log(u'(getUrl) ERROR - ERROR - ERROR : ########## {0} === {1} ##########'.format(url, failure))
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

def post_url(url, postdata, headers={}, json = False, critical=False):
    log(u'post: {0}, {1}'.format(url, headers))
    new_headers = {}
    new_headers.update(headers)
    if json:
        new_headers.update({'Content-Type': 'application/json; charset=utf-8'})
    try:
        request = urlopen(Request(url, headers=new_headers, data=postdata.encode('utf-8')))
    except HTTPError as e:
        failure = str(e)
        if hasattr(e, 'code'):
            log(u'(getUrl) ERROR - ERROR - ERROR : ########## {0} === {1} === {2} ##########'.format(url, postdata, failure))
        elif hasattr(e, 'reason'):
            log(u'(getUrl) ERROR - ERROR - ERROR : ########## {0} === {1} === {2} ##########'.format(url, postdata, failure))
        try:
            data = u''
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
            pass
        if critical:
            if hasattr(e, 'code') and getattr(e, 'code') == 422:
                kodiutils.notification(u'ERROR GETTING URL', kodiutils.get_string(32003))
            else:
                kodiutils.notification(u'ERROR GETTING URL', failure)
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
    return data.decode('utf-8')

def run():
    plugin.run()

def log(info):
    if kodiutils.get_setting_as_bool('debug'):
        try:
            logger.warning(info)
        except UnicodeDecodeError:
            logger.warning(u'UnicodeDecodeError on logging')
            logger.warning(info.decode('utf-8'))
