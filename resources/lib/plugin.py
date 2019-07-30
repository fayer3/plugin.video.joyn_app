# -*- coding: utf-8 -*-

import routing
import logging
import xbmcaddon
import xbmcgui
import xbmcvfs
import xbmc
import xbmcplugin
from resources.lib import kodiutils
from resources.lib import kodilogging
from resources.lib import ids
from resources.lib import xxtea
from xbmcgui import ListItem
from xbmcplugin import addDirectoryItem, endOfDirectory, setResolvedUrl, setContent
from distutils.version import LooseVersion

import codecs

try:
    import inputstreamhelper
    inputstream = True
except ImportError:
    inputstream = False

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

import locale
import time
from datetime import date, datetime, timedelta
import hashlib
import json
import gzip
import sys
import re
import base64
import random

try:
    from multiprocessing.pool import ThreadPool
    multiprocess = True
except ImportError:
    multiprocess = False

from six.moves.html_parser import HTMLParser
html_parser = HTMLParser()

ADDON = xbmcaddon.Addon()
logger = logging.getLogger(ADDON.getAddonInfo('id'))
kodilogging.config()
plugin = routing.Plugin()

__profile__ = xbmc.translatePath(ADDON.getAddonInfo('profile'))

if not xbmcvfs.exists(__profile__):
    xbmcvfs.mkdirs(__profile__)

favorites_file_path = __profile__+"favorites.json"
favorites = {}

icon_path = ADDON.getAddonInfo('path')+"/resources/logos/{0}.png"
setContent(plugin.handle, 'tvshows')
#setContent(plugin.handle, '')

@plugin.route('/')
def index():
    content = json.loads(get_url(ids.overview_url, critical = True))
    for item in content['response']['blocks']:
        if item['type'] != 'ResumeLane':
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
    endOfDirectory(plugin.handle)

@plugin.route('/fetch/id=<fetch_id>/type=<type>/')
def show_fetch(fetch_id, type):
    query = json.loads(unquote(plugin.args['query'][0]))
    header = json.loads(unquote(plugin.args['header'][0]))
    content = fetch(fetch_id, query, header)
    add_from_fetch(content, type)
    endOfDirectory(plugin.handle)

def fetch(fetch_id, query, header):
    url = ids.fetch_url.format(fetch_id)
    url += '?'
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
        addDirectoryItem(plugin.handle,plugin.url_for(
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
    content = json.loads(get_url(ids.livestream_url, critical=True))
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
            if desc['type'] == 'main':
                description = desc['text']
        listitem.setProperty('IsPlayable', 'true')
        listitem.setInfo(type='Video', infoLabels={'Title': name, 'Plot': description, 'TvShowTitle': name, 'mediatype': 'video'})
        if len(item['metadata']['de']['livestreams']) > 0:
            addDirectoryItem(plugin.handle,plugin.url_for(
                play_live, stream_id=item['metadata']['de']['livestreams'][0]['streamId'], brand=name.encode('utf-8')), listitem)


@plugin.route('/channel/id=<channel_id>/')
def show_channel(channel_id):
    current = 0
    content = json.loads(get_url(ids.channel_url.format(current, channel_id), critical=True))
    add_series_from_fetch(content)
    while len(content['response']['data']) == ids.channel_limit:
        current += ids.channel_limit
        content = json.loads(get_url(ids.channel_url.format(current, channel_id), critical=True))
        add_series_from_fetch(content)
    endOfDirectory(plugin.handle)

@plugin.route('/seasons/id=<show_id>/')
def show_seasons(show_id):
    content_tvshow = json.loads(get_url(ids.tvshow_url.format(show_id)+ids.tvshow_selection, critical = True))
    icon=''
    poster = ''
    fanart = ''
    thumbnail = ''
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
    content = json.loads(get_url(ids.seasons_url.format(show_id)+ids.seasons_selection, critical = True))
    for item in content['response']['data']:
        name = ''
        for title in item['metadata']['de']['titles']:
            if title['type'] == 'main':
                name = title['text']
        listitem = ListItem(name)
        # get images
        icon=''
        for image in item['metadata']['de']['images']:
            if image['type'] == 'PRIMARY':
                icon = ids.image_url.format(image['url'])
        listitem.setArt({'icon': icon, 'thumb': thumbnail, 'poster': poster, 'fanart': fanart})
        description = ''
        for desc in item['metadata']['de']['descriptions']:
            if desc['type'] == 'main':
                description = desc['text']
        listitem.setInfo(type='Video', infoLabels={'Title': name, 'Plot': description, 'TvShowTitle': name})
        addDirectoryItem(plugin.handle,plugin.url_for(
            show_season, season_id=item['id']), listitem, True)
    endOfDirectory(plugin.handle)

@plugin.route('/season/id=<season_id>/')
def show_season(season_id):
    setContent(plugin.handle, 'tvshows')
    content = json.loads(get_url(ids.season_url.format(season_id)+ids.season_selection, critical = True))
    for item in content['response']['data']:
        goDATE = None
        toDATE = None
        startTIMES = ""
        endTIMES = ""
        Note_1 = ""
        if 'visibilities' in item:
            startDATES = datetime.fromtimestamp(int(item['visibilities'][0]['startsAt']))
            startTIMES = startDATES.strftime('%d.%m.%Y - %H:%M')
            goDATE =  startDATES.strftime('%d.%m.%Y')
            endDATES = datetime.fromtimestamp(int(item['visibilities'][0]['endsAt']))
            endTIMES = endDATES.strftime('%d.%m.%Y - %H:%M')
            toDATE =  endDATES.strftime('%d.%m.%Y')
        if startTIMES and endTIMES: Note_1 = kodiutils.get_string(32002).format(startTIMES, endTIMES)
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
        if not icon:
            icon = thumbnail
        listitem.setArt({'icon': icon, 'thumb': thumbnail, 'poster': poster, 'fanart': fanart})
        description = ''
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
    #playitem = ListItem(label='video', path='https://gist.githubusercontent.com/fayer3/0ee27fe789128467e28221c256fafdff/raw/5a88c6ab1b05fd393f1621ee8561f67a8e8515ab/gistfile1.txt')
    #playitem = ListItem(label='video', path=ADDON.getAddonInfo('path')+"/resources/temp.mpd")
    playitem = ListItem(label='video', path='https://cf.t1p-vod-playout-prod.aws.route71.net/origin/116021_a_pr64q9mojah_2019-7-17_23-1/a_pr64q9mojah.ism/.mpd?filter=(type%3D%3D%22video%22%26%26MaxHeight%3C%3D576)%7C%7C(type%3D%3D%22audio%22%26%26FourCC%3D%3D%22AACL%22%26%26systemBitrate%3E100000)')
    playitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
    playitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    playitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
    playitem.setProperty('inputstream.adaptive.license_key', 'https://prosieben-ctr.live.ott.irdeto.com/licenseServer/widevine/v1/prosieben/license?contentId=a_pr64q9mojah&ls_session=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjFiMTJjM2ViLTExZGUtNDhlNi1hY2Y3LTEwYzliNzdiMmY0ZCJ9.eyJqdGkiOiJkZWY3M2QyMC1hY2Q0LTExZTktODVkNi01YmRkZGIyOTExNjMiLCJzdWIiOiJhbm9ueW1vdXMtdXNlcnMiLCJhaWQiOiJwcm9zaWViZW4iLCJpc3MiOiJwcm9zaWViZW4iLCJpYXQiOjE1NjM4MzY1ODgsImV4cCI6MTU2Mzg1MDk4OH0.-y_SoHK_0Ee1_c5SdHCy0gVTJrYfP_OipCD-3_T2N7g|'+'|R{SSM}|')

    setResolvedUrl(plugin.handle, True, playitem)

@plugin.route('/category/<category_id>')
def show_category(category_id):
    if category_id == "favorites":
        xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_LABEL)
        global favorites
        if not favorites and xbmcvfs.exists(favorites_file_path):
            favorites_file = xbmcvfs.File(favorites_file_path)
            favorites = json.load(favorites_file)
            favorites_file.close()

        for item in favorites:
            listitem = ListItem(favorites[item]["name"])
            listitem.setArt({'icon': favorites[item]["icon"], 'thumb':favorites[item]["icon"], 'poster':favorites[item]["icon"], 'fanart' : favorites[item]["fanart"]})
            addDirectoryItem(plugin.handle, url=item,
                listitem=listitem, isFolder=True)
    else:
        content = json.loads(get_url(ids.overview_url, critical = True))
        for category in content['response']['blocks']:
            if category_id == category['id']:
                if multiprocess:
                    threads = []
                    pool = ThreadPool(processes=kodiutils.get_setting_as_int("simultanious_requests"))
                for item in category['items']:
                    query = []
                    header = []
                    for param in item['fetch']['requiredParams']:
                        if param['in'] == 'query':
                            query.append(param['name'])
                        elif param['in'] == 'header':
                            header.append(param['name'])
                        else:
                            kodiutils.notification("ERROR", "new param location " + param['in'])
                            log("new param location " + param['in'])
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

@plugin.route('/episode/<episode_id>/')
def play_episode(episode_id):
    if LooseVersion('18.0') > LooseVersion(xbmc.getInfoLabel('System.BuildVersion')):
        log("version is: " + xbmc.getInfoLabel('System.BuildVersion'))
        kodiutils.notification('ERROR', kodiutils.get_string(32025))
        setResolvedUrl(plugin.handle, False, ListItem('none'))
        return
    content = json.loads(get_url(ids.video_info_url.format(episode_id), critical = True))
    player_config_data = json.loads(get_url(ids.player_config_url, cache = True, critical = True))
    player_config = json.loads(base64.b64decode(xxtea.decryptHexToStringss(player_config_data['toolkit']['psf'], ids.xxtea_key)))
    nuggvars_data = get_url(ids.nuggvars_url, critical=True)
    psf_config = json.loads(get_url(ids.psf_config_url, critical = True))
    playoutBaseUrl = psf_config['default']['vod']['playoutBaseUrl']
    entitlementBaseUrl = psf_config['default']['vod']['entitlementBaseUrl']

    postdata = '{"access_id":"'+ player_config['accessId']+'","content_id":"'+episode_id+'","content_type":"VOD"}'
    if kodiutils.get_setting_as_bool('fake_ip'):
        entitlement_token_data = json.loads(post_url(entitlementBaseUrl+ids.entitlement_token_url, postdata=postdata, headers={'x-api-key': psf_config['default']['vod']['apiGatewayKey'], 'x-forwarded-for':'53.'+str(random.randint(0,256))+'.'+str(random.randint(0,256))+'.'+str(random.randint(0,256))}, json = True, critical=True))
    else:
        entitlement_token_data = json.loads(post_url(entitlementBaseUrl+ids.entitlement_token_url, postdata=postdata, headers={'x-api-key': psf_config['default']['vod']['apiGatewayKey']}, json = True, critical=True))

    tracking = content['response']['tracking']
    genres='["'+'","'.join(tracking['genres'])+'"]'

    nuggvars = nuggvars_data.replace('{"','').replace(',"url":""}','').replace('":','=').replace(',"','&')

    clientData = base64.b64encode((ids.clientdata.format(nuggvars=nuggvars[:-1], episode_id=episode_id, duration=content['response']['video']['duration'], brand=tracking['channel'], genres=genres, tvshow_id=tracking['tvShow']['id'])).encode('utf-8')).decode('utf-8')
    log('clientData: ' + clientData)

    sig = episode_id + ',' + entitlement_token_data['entitlement_token'] + ',' + clientData + codecs.encode(ids.xxtea_key.encode('utf-8'),'hex').decode('utf-8')
    sig = hashlib.sha1(sig.encode('UTF-8')).hexdigest()

    video_url = playoutBaseUrl+ids.video_playback_url.format(episode_id=episode_id, entitlement_token=entitlement_token_data['entitlement_token'], clientData=clientData, sig=sig)

    playitem = ListItem(content['response']['video']['titles']['default'])

    video_data = json.loads(post_url(video_url,postdata='server', critical=True))
    if video_data['vmap']:
        #got add try again
        video_data = json.loads(post_url(video_url,postdata='server', critical=True))
    if video_data['vmap']:
        kodiutils.notification('INFO', kodiutils.get_string(32005))
        setResolvedUrl(plugin.handle, False, playitem)
        return

    is_helper = None
    if video_data['drm'] != 'widevine':
        kodiutils.notification('ERROR', kodiutils.get_string(32004).format(video_data['drm']))
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
        playitem.setPath(video_data['videoUrl'].rpartition("?")[0]+"|User-Agent=vvs-native-android/1.0.10 (Linux;Android 7.1.1) ExoPlayerLib/2.8.1")
        #playitem.path= = ListItem(label=xbmc.getInfoLabel('Container.ShowTitle'), path=urls["urls"]["dash"][drm_name]["url"]+"|User-Agent=vvs-native-android/1.0.10 (Linux;Android 7.1.1) ExoPlayerLib/2.8.1")
        playitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        playitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        playitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
        playitem.setProperty('inputstream.adaptive.license_key', video_data['licenseUrl'] +"|User-Agent=vvs-native-android/1.0.10 (Linux;Android 7.1.1) ExoPlayerLib/2.8.1" +'|R{SSM}|')
        setResolvedUrl(plugin.handle, True, playitem)
    else:
        kodiutils.notification('ERROR', kodiutils.get_string(32019).format(drm))
        setResolvedUrl(plugin.handle, False, playitem)

@plugin.route('/live/<stream_id>/<brand>/')
def play_live(stream_id, brand):
    if LooseVersion('18.0') > LooseVersion(xbmc.getInfoLabel('System.BuildVersion')):
        log("version is: " + xbmc.getInfoLabel('System.BuildVersion'))
        kodiutils.notification('ERROR', kodiutils.get_string(32025))
        setResolvedUrl(plugin.handle, False, ListItem('none'))
        return
    player_config_data = json.loads(get_url(ids.player_config_url, cache = True, critical = True))
    player_config = json.loads(base64.b64decode(xxtea.decryptHexToStringss(player_config_data['toolkit']['psf'], ids.xxtea_key)))
    psf_config = json.loads(get_url(ids.psf_config_url, critical = True))
    playoutBaseUrl = psf_config['default']['live']['playoutBaseUrl']
    entitlementBaseUrl = psf_config['default']['live']['entitlementBaseUrl']

    postdata = '{"access_id":"'+ player_config['accessId']+'","content_id":"'+stream_id+'","content_type":"LIVE"}'
    if kodiutils.get_setting_as_bool('fake_ip'):
        entitlement_token_data = json.loads(post_url(entitlementBaseUrl+ids.entitlement_token_url, postdata=postdata, headers={'x-api-key': psf_config['default']['live']['apiGatewayKey'], 'x-forwarded-for': '53.'+str(random.randint(0,256))+'.'+str(random.randint(0,256))+'.'+str(random.randint(0,256))}, json = True, critical=True))
    else:
        entitlement_token_data = json.loads(post_url(entitlementBaseUrl+ids.entitlement_token_url, postdata=postdata, headers={'x-api-key': psf_config['default']['live']['apiGatewayKey']}, json = True, critical=True))

    clientData = base64.b64encode((ids.clientdata_live.format(stream_id=stream_id, brand=brand)).encode('utf-8')).decode('utf-8')
    log('clientData: ' + clientData)

    sig = stream_id + ',' + entitlement_token_data['entitlement_token'] + ',' + clientData + codecs.encode(ids.xxtea_key.encode('utf-8'),'hex').decode('utf-8')
    sig = hashlib.sha1(sig.encode('UTF-8')).hexdigest()

    video_url = playoutBaseUrl+ids.live_playback_url.format(stream_id=stream_id, entitlement_token=entitlement_token_data['entitlement_token'], clientData=clientData, sig=sig)

    playitem = ListItem(brand)

    video_data = json.loads(post_url(video_url, postdata='server', critical=True))
    if video_data['vmap']:
        #got add try again
        video_data = json.loads(post_url(video_url, postdata='server', critical=True))
    if video_data['vmap']:
        kodiutils.notification('INFO', kodiutils.get_string(32005))
        setResolvedUrl(plugin.handle, False, playitem)
        return

    is_helper = None
    if video_data['drm'] != 'widevine':
        kodiutils.notification('ERROR', kodiutils.get_string(32004).format(video_data['drm']))
        return
    video_url = video_data['videoUrl']
    video_url_data = get_url(video_url, critical = True)

    # check base urls
    base_urls = re.findall('<BaseURL>(.*?)</BaseURL>',video_url_data)
    if len(base_urls) > 1:
        if base_urls[0].startswith('http'):
            video_url = base_urls[0]+base_urls[1]+'cenc-default.mpd'

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
        playitem.setPath(video_url+"|User-Agent=vvs-native-android/1.0.10 (Linux;Android 7.1.1) ExoPlayerLib/2.8.1")
        #playitem.path= = ListItem(label=xbmc.getInfoLabel('Container.ShowTitle'), path=urls["urls"]["dash"][drm_name]["url"]+"|User-Agent=vvs-native-android/1.0.10 (Linux;Android 7.1.1) ExoPlayerLib/2.8.1")
        playitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        playitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        playitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
        playitem.setProperty("inputstream.adaptive.manifest_update_parameter", "full")
        playitem.setProperty('inputstream.adaptive.license_key', video_data['licenseUrl'] +"|User-Agent=vvs-native-android/1.0.10 (Linux;Android 7.1.1) ExoPlayerLib/2.8.1" +'|R{SSM}|')
        setResolvedUrl(plugin.handle, True, playitem)
    else:
        kodiutils.notification('ERROR', kodiutils.get_string(32019).format(drm))
        setResolvedUrl(plugin.handle, False, playitem)

def utc_to_local(dt):
    if time.localtime().tm_isdst: return dt - timedelta(seconds=time.altzone)
    else: return dt - timedelta(seconds=time.timezone)

def add_favorites_folder(path, name, icon, fanart):
    global favorites
    if not favorites and xbmcvfs.exists(favorites_file_path):
        favorites_file = xbmcvfs.File(favorites_file_path)
        favorites = json.load(favorites_file)
        favorites_file.close()

    if not favorites or path not in favorites:
        # add favorites folder
        #addDirectoryItem(plugin.handle, url=plugin.url_for(add_favorite, query="%s***%s###%s###%s" % (path, name, icon, fanart)), listitem=ListItem(kodiutils.get_string(32004)))
        addDirectoryItem(plugin.handle, url=plugin.url_for(add_favorite, path=quote(codecs.encode(path, 'UTF-8')), name=quote(codecs.encode(name, 'UTF-8')), icon=quote(codecs.encode(icon, 'UTF-8')), fanart=quote(codecs.encode(fanart, 'UTF-8'))), listitem=ListItem(kodiutils.get_string(32008)))
    else:
        # remove favorites
        addDirectoryItem(plugin.handle, url=plugin.url_for(remove_favorite, query=quote(codecs.encode(path, 'UTF-8'))),
            listitem=ListItem(kodiutils.get_string(32009)))

@plugin.route('/add_fav/')
def add_favorite():
    #data = plugin.args['query'][0].split('***')
    path = unquote(plugin.args['path'][0])
    name = unquote(plugin.args['name'][0])
    icon = ""
    if 'icon' in plugin.args:
        icon = unquote(plugin.args['icon'][0])
    fanart = ""
    if 'fanart' in plugin.args:
        fanart = unquote(plugin.args['fanart'][0])
    # load favorites
    global favorites
    if not favorites and xbmcvfs.exists(favorites_file_path):
        favorites_file = xbmcvfs.File(favorites_file_path)
        favorites = json.load(favorites_file)
        favorites_file.close()

    #favorites.update({data[0] : data[1]})
    favorites.update({path : {"name" : name, "icon" : icon, "fanart" : fanart}})
    # load favorites
    favorites_file = xbmcvfs.File(favorites_file_path, 'w')
    json.dump(favorites, favorites_file, indent=2)
    favorites_file.close()

    try:
        kodiutils.notification(kodiutils.get_string(32010), kodiutils.get_string(32011).format(codecs.decode(name, 'utf-8')))
    except TypeError:
        kodiutils.notification(kodiutils.get_string(32010), kodiutils.get_string(32011).format(codecs.decode(bytes(name, 'utf-8'), 'utf-8')))
    xbmc.executebuiltin('Container.Refresh')
    setResolvedUrl(plugin.handle, True, ListItem("none"))

@plugin.route('/remove_fav')
def remove_favorite():
    data = unquote(plugin.args['query'][0])
    # load favorites
    global favorites
    if not favorites and xbmcvfs.exists(favorites_file_path):
        favorites_file = xbmcvfs.File(favorites_file_path)
        favorites = json.load(favorites_file)
        favorites_file.close()

    name = favorites[data]["name"]
    del favorites[data]
    # load favorites
    favorites_file = xbmcvfs.File(favorites_file_path, 'w')
    json.dump(favorites, favorites_file, indent=2)
    favorites_file.close()

    kodiutils.notification(kodiutils.get_string(32010), kodiutils.get_string(32012).format(name))
    xbmc.executebuiltin('Container.Refresh')
    setResolvedUrl(plugin.handle, True, ListItem("none"))

def get_url(url, headers={}, cache=False, critical=False):
    log(url)
    new_headers = {}
    new_headers.update(headers)
    if cache == True:
        new_headers.update({"If-Modified-Since": ids.get_config_tag(url)})
    new_headers.update({"User-Agent": ids.user_agent, "Accept-Encoding":"gzip", 'key': ids.middleware_token})
    try:
        request = urlopen(Request(url, headers=new_headers))
    except HTTPError as e:
        if cache and e.code == 304:
            return ids.get_config_cache(url)
        failure = str(e)
        if hasattr(e, 'code'):
            log("(getUrl) ERROR - ERROR - ERROR : ########## {0} === {1} ##########".format(url, failure))
        elif hasattr(e, 'reason'):
            log("(getUrl) ERROR - ERROR - ERROR : ########## {0} === {1} ##########".format(url, failure))
        try:
            data = ''
            if e.info().get('Content-Encoding') == 'gzip':
                # decompress content
                buffer = StringIO(e.read())
                deflatedContent = gzip.GzipFile(fileobj=buffer)
                data = deflatedContent.read()
            else:
                data = e.read()
            log('Error: ' + data.decode('utf-8'))
        except:
            log('couldn\'t read Error content')
            pass
        if critical:
            kodiutils.notification("ERROR GETTING URL", failure)
            return sys.exit(0)
        else:
            return ""

    if request.info().get('Content-Encoding') == 'gzip':
        # decompress content
        buffer = StringIO(request.read())
        deflatedContent = gzip.GzipFile(fileobj=buffer)
        data = deflatedContent.read()
    else:
        data = request.read()

    if cache:
        ids.set_config_cache(url, data, request.info().get('Last-Modified'))
    return data.decode('utf-8')

def post_url(url, postdata, headers={}, json = False, critical=False):
    log(url + str(headers))
    new_headers = {}
    new_headers.update(headers)
    if json:
        new_headers.update({'Content-Type': 'application/json; charset=utf-8'})
    try:
        request = urlopen(Request(url, headers=new_headers, data=postdata.encode('utf-8')))
    except HTTPError as e:
        failure = str(e)
        if hasattr(e, 'code'):
            log("(getUrl) ERROR - ERROR - ERROR : ########## {0} === {1} === {2} ##########".format(url, postdata, failure))
        elif hasattr(e, 'reason'):
            log("(getUrl) ERROR - ERROR - ERROR : ########## {0} === {1} === {2} ##########".format(url, postdata, failure))
        try:
            data = ''
            if e.info().get('Content-Encoding') == 'gzip':
                # decompress content
                buffer = StringIO(e.read())
                deflatedContent = gzip.GzipFile(fileobj=buffer)
                data = deflatedContent.read()
            else:
                data = e.read()
            log('Error: ' + data.decode('utf-8'))
        except:
            log('couldn\'t read Error content')
            pass
        if critical:
            if hasattr(e, 'code') and getattr(e, 'code') == 422:
                kodiutils.notification("ERROR GETTING URL", kodiutils.get_string(32003))
            else:
                kodiutils.notification("ERROR GETTING URL", failure)
            return sys.exit(0)
        else:
            return ""

    if request.info().get('Content-Encoding') == 'gzip':
        # decompress content
        buffer = StringIO(request.read())
        deflatedContent = gzip.GzipFile(fileobj=buffer)
        data = deflatedContent.read()
    else:
        data = request.read()
    return data.decode('utf-8')

def get_listitem(name="", icon="", fanart="", channel={}):
    if channel:
        listitem = ListItem(channel["name"])
        listitem.setProperty('IsPlayable', 'true')
        images = json.loads(channel["images_json"])
        if images:
            if "image_base" in images and images["image_base"]:
                listitem.setArt({'icon':images["image_base"], 'thumb':images["image_base"], 'poster':images["image_base"]})
            else:
                listitem.setArt({'icon':images["icon_1"], 'thumb':images["icon_1"], 'poster':images["icon_1"]})
        if "next_program" in channel:
            #'Title': channel["name"]
            listitem.setInfo(type='Video', infoLabels={'Title': listitem.getLabel(), 'Plot': channel["next_program"]["name"]+'[CR]'+channel["next_program"]["description"], 'mediatype': 'video'})
            program_images = json.loads(channel["next_program"]["images_json"])
            if program_images:
                listitem.setArt({'fanart' : program_images["image_base"]})
    else:
        listitem = ListItem(name)
        listitem.setProperty('IsPlayable', 'true')
        listitem.setInfo(type='Video', infoLabels={'mediatype': 'video'})
        if icon != "":
            listitem.setArt({'icon':icon, 'thumb':icon, 'poster':icon})
        if fanart != "":
            listitem.setArt({'fanart':fanart})
    return listitem

def run():
    plugin.run()

def log(info):
    if kodiutils.get_setting_as_bool("debug"):
        logger.warning(info)
