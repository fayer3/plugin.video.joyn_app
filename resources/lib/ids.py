import json
import xbmc
import xbmcaddon
import xbmcvfs
import logging
logger = logging.getLogger(xbmcaddon.Addon().getAddonInfo('id'))

__profile__ = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))

if not xbmcvfs.exists(__profile__):
    xbmcvfs.mkdirs(__profile__)

cache_file_path = __profile__+"config_cache.json"
tag_file_path = __profile__+"tag_cache.json"

# data for requests

user_agent = 'Joyn Android App build/301003149 release/3.1.0'

# from app
middleware_token = '1ec991118fe49ca44c185ee6a86354ef'

# from https://psf.player.v0.maxdome.cloud/dist/playback-source-fetcher.min.js
xxtea_key = '5C7838365C7864665C786638265C783064595C783935245C7865395C7838323F5C7866333D3B5C78386635'

config_url = 'https://playerconfig.prd.platform.s.joyn.de/df0aba535c694114d8e2b193b9affd97.json'

overview_url = 'https://middleware.p7s1.io/joyn/v1/ui?path=/'
#livestream_url = 'https://middleware.p7s1.io/joyn/v1/brands?selection={data{id, channelId ,agofCodes,metadata}}&streamIds=true&mock=false'
livestream_url = 'https://middleware.p7s1.io/joyn/v1/brands?selection=%7Bdata%7Bid%2C%20channelId%20%2CagofCodes%2Cmetadata%7D%7D&streamIds=true&mock=false'

fetch_url = 'https://middleware.p7s1.io/joyn/v1/fetch/{0}'
#fetch_selection = 'selection={data{id,visibilities, channelId ,agofCodes,duration,metadata{de}}}'
fetch_selection = 'selection=%7Bdata%7Bid%2Cvisibilities%2C%20channelId%20%2CagofCodes%2Cduration%2Cmetadata%7Bde%7D%7D%7D'

seasons_url = 'https://middleware.p7s1.io/joyn/v1/seasons?tvShowId={0}'
#seasons_selection = '&subType=Hauptfilm&sortBy=seasonsOrder&selection={data{id,channelId,visibilities,duration,metadata{de}}}&sortAscending=true'
seasons_selection = '&subType=Hauptfilm&sortBy=seasonsOrder&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D&sortAscending=true'

season_url = 'https://middleware.p7s1.io/joyn/v1/videos?seasonId={0}'
#season_selection = '&sortBy=seasonsOrder&sortAscending=true&skip=0&subType=Hauptfilm&selection={data{id,channelId,visibilities,duration,metadata{de}}}'
season_selection = '&sortBy=seasonsOrder&sortAscending=true&skip=0&subType=Hauptfilm&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D'

tvshow_url = 'https://middleware.p7s1.io/joyn/v1/tvshows?ids={0}'
#tvshow_selection = '&limit=1&subType=Hauptfilm&selection={data{id,channelId,visibilities,duration,metadata{de}}}&filter=visible&type=tvShow'
tvshow_selection = '&limit=1&subType=Hauptfilm&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D&filter=visible&type=tvShow'

channel_url = 'https://middleware.p7s1.io/joyn/v1/tvshows?skip={0}&limit=5000&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D&filter=visible&type=tvShow%2Cmovie&channelId={1}'
channel_limit = 5000

video_info_url = 'https://middleware.p7s1.io/joyn/v1/metadata/video/{0}?country=de&devicetype=phone&recommendations=2'

image_url = '{0}/profile:original'

player_config_url = 'https://playerconfig.prd.platform.s.joyn.de/df0aba535c694114d8e2b193b9affd97.json'

psf_config_url = 'https://psf.player.v0.maxdome.cloud/config/psf.json'

entitlement_token_url = 'entitlement-token/anonymous'

nuggvars_url = 'https://71iapp-cp.nuggad.net/rc?nuggn=2011964291&nuggsid=1282618500&nuggtg=TV_DRAMA,EDITORIAL_CONT_VIDEO&tok='

video_playback_url = 'playout/video/{episode_id}?entitlement_token={entitlement_token}&clientData={clientData}&sig={sig}'
live_playback_url = 'playout/channel/{stream_id}?entitlement_token={entitlement_token}&clientData={clientData}&sig={sig}'

clientdata = '{{"adconfigurl":null,"idfa":"","noAdCooldown":true,"npa":false,"nuggvars":"{nuggvars}","ppid":"","startTime":0,"videoId":"{episode_id}","duration":{duration},"brand":"{brand}","genre":{genres},"tvshowid":"{tvshow_id}"}}'

clientdata_live = '{{"adconfigurl":null,"idfa":"","noAdCooldown":true,"npa":false,"nuggvars":"0","ppid":"","startTime":0,"videoId":"{stream_id}","brand":"{brand}","genre":[]}}'

config_cache = {}
config_tag = {}

def get_config_url():
    return player_config_url

def get_config_cache(url):
    global config_cache
    if not config_cache and xbmcvfs.exists(cache_file_path):
        cache_file = xbmcvfs.File(cache_file_path)
        config_cache = json.load(cache_file)
        cache_file.close()
    if url in config_cache:
        return config_cache[url]
    return ""

def get_config_tag(url):
    global config_tag
    if not config_tag and xbmcvfs.exists(tag_file_path):
        tag_file = xbmcvfs.File(tag_file_path)
        config_tag = json.load(tag_file)
        tag_file.close()
    if url in config_tag:
        return config_tag[url]
    return ""

def set_config_cache(url, data, tag):
    global config_cache
    if not config_cache and xbmcvfs.exists(cache_file_path):
        cache_file = xbmcvfs.File(cache_file_path)
        config_cache = json.load(cache_file)
        cache_file.close()
    config_cache.update({url : data})
    global config_tag
    if not config_tag and xbmcvfs.exists(tag_file_path):
        tag_file = xbmcvfs.File(tag_file_path)
        config_tag = json.load(tag_file)
        tag_file.close()
    config_tag.update({url : tag})
    #save dictionary
    cache_file = xbmcvfs.File(cache_file_path, 'w')
    json.dump(config_cache, cache_file, indent=2)
    cache_file.close()
    tag_file = xbmcvfs.File(tag_file_path, 'w')
    json.dump(config_tag, tag_file, indent=2)
    cache_file.close()
