import json
import xbmc
import xbmcaddon
import xbmcvfs
import logging
logger = logging.getLogger(xbmcaddon.Addon().getAddonInfo('id'))

__profile__ = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))

if not xbmcvfs.exists(__profile__):
    xbmcvfs.mkdirs(__profile__)

cache_file_path = __profile__ + u'config_cache.json'
tag_file_path = __profile__ + u'tag_cache.json'

# data for requests

user_agent = u'Joyn Android App build/301003149 release/3.1.0'

# from app
middleware_token = u'1ec991118fe49ca44c185ee6a86354ef'

# from https://psf.player.v0.maxdome.cloud/dist/playback-source-fetcher.min.js
xxtea_key = u'5C7838365C7864665C786638265C783064595C783935245C7865395C7838323F5C7866333D3B5C78386635'

config_url = u'https://playerconfig.prd.platform.s.joyn.de/df0aba535c694114d8e2b193b9affd97.json'

base_url = u'https://middleware.p7s1.io/joyn/v1/'

overview_url = base_url + u'ui?path=/'
#livestream_url = 'https://middleware.p7s1.io/joyn/v1/brands?selection={data{id, channelId ,agofCodes,metadata}}&streamIds=true&mock=false'
livestream_url = base_url + u'brands?selection=%7Bdata%7Bid%2C%20channelId%20%2CagofCodes%2Cmetadata%7D%7D&streamIds=true&mock=false'

#https://middleware.p7s1.io/joyn/v1/epg?selection={totalCount,data{id,title,description,tvShow,type,productionYear,tvChannelName,channelId,startTime,endTime,repeatTime,video,genres{type,title},images(subType:"cover,logo,art_direction"){url,subType}}}&skip=0&limit=1000&from={0}&to={1}&sortBy=startTime&sortAscending=true'
epg_url = base_url + u'epg?selection=%7BtotalCount%2Cdata%7Bid%2Ctitle%2Cdescription%2CtvShow%2Ctype%2CproductionYear%2CtvChannelName%2CchannelId%2CstartTime%2CendTime%2CrepeatTime%2Cvideo%2Cgenres%7Btype%2Ctitle%7D%2Cimages%28subType%3A%22cover%2Clogo%2Cart_direction%22%29%7Burl%2CsubType%7D%7D%7D&skip=0&limit=1000&from={0}&to={1}&sortBy=startTime&sortAscending=true'

epg_now_url = base_url + u'epg/now?selection=%7BtotalCount%2Cdata%7Bid%2Ctitle%2Cdescription%2CtvShow%2Ctype%2CproductionYear%2CtvChannelName%2CchannelId%2CstartTime%2CendTime%2CrepeatTime%2Cvideo%2Cgenres%7Btype%2Ctitle%7D%2Cimages%28subType%3A%22cover%2Clogo%2Cart_direction%22%29%7Burl%2CsubType%7D%7D%7D&skip=0&limit=5000&sortAscending=true'

epg_channel_url = base_url + u'epg?selection=%7BtotalCount%2Cdata%7Bid%2Ctitle%2Cdescription%2CtvShow%2Ctype%2CproductionYear%2CtvChannelName%2CchannelId%2CstartTime%2CendTime%2CrepeatTime%2Cvideo%2Cgenres%7Btype%2Ctitle%7D%2Cimages%28subType%3A%22cover%2Clogo%2Cart_direction%22%29%7Burl%2CsubType%7D%7D%7D&skip=0&limit=1000&sortBy=startTime&sortAscending=true&channelId={channel}'

fetch_url = base_url + u'fetch/{0}'
#fetch_selection = 'selection={data{id,visibilities, channelId ,agofCodes,duration,metadata{de}}}'
fetch_selection = u'selection=%7Bdata%7Bid%2Cvisibilities%2C%20channelId%20%2CagofCodes%2Cduration%2Cmetadata%7Bde%7D%7D%7D'

seasons_url = base_url + u'seasons?tvShowId={0}&subType=Hauptfilm&sortBy=seasonsOrder&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D&sortAscending=true'
#seasons_selection = '&subType=Hauptfilm&sortBy=seasonsOrder&selection={data{id,channelId,visibilities,duration,metadata{de}}}&sortAscending=true'

season_url = base_url + u'videos?seasonId={0}&sortBy=seasonsOrder&sortAscending=true&skip=0&subType=Hauptfilm&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2CtvShow%2Cmetadata%7Bde%7D%7D%7D'
#season_selection = '&sortBy=seasonsOrder&sortAscending=true&skip=0&subType=Hauptfilm&selection={data{id,channelId,visibilities,duration,metadata{de}}}'

tvshow_url = base_url + u'tvshows?ids={0}&limit=1&subType=Hauptfilm&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D&filter=visible&type=tvShow'
#tvshow_selection = '&limit=1&subType=Hauptfilm&selection={data{id,channelId,visibilities,duration,metadata{de}}}&filter=visible&type=tvShow'

channel_url = base_url + u'tvshows?skip={0}&limit=5000&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D&filter=visible&type=tvShow%2Cmovie&channelId={1}'
channel_limit = 5000

search_tvshow_url = base_url + u'tvshows?search={0}&limit=5000&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D&filter=visible&type=tvShow'
search_movie_url = base_url + u'tvshows?search={0}&limit=5000&subType=Hauptfilm&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D&filter=visible&type=movie'
search_limit = 5000

video_info_url = base_url + u'metadata/video/{0}?country=de&devicetype=phone&recommendations=2'

image_url = u'{0}/profile:original'

player_config_url = u'https://playerconfig.prd.platform.s.joyn.de/df0aba535c694114d8e2b193b9affd97.json'

psf_config_url = u'https://psf.player.v0.maxdome.cloud/config/psf.json'

entitlement_token_url = u'entitlement-token/anonymous'

nuggvars_url = u'https://71iapp-cp.nuggad.net/rc?nuggn=2011964291&nuggsid=1282618500&nuggtg=TV_DRAMA,EDITORIAL_CONT_VIDEO&tok='

video_playback_url = u'playout/video/{episode_id}?entitlement_token={entitlement_token}&clientData={clientData}&sig={sig}'
live_playback_url = u'playout/channel/{stream_id}?entitlement_token={entitlement_token}&clientData={clientData}&sig={sig}'

clientdata = u'{{"adconfigurl":null,"idfa":"","noAdCooldown":true,"npa":false,"nuggvars":"{nuggvars}","ppid":"","startTime":0,"videoId":"{episode_id}","duration":{duration},"brand":"{brand}","genre":{genres},"tvshowid":"{tvshow_id}"}}'

clientdata_live = u'{{"adconfigurl":null,"idfa":"","noAdCooldown":true,"npa":false,"nuggvars":"0","ppid":"","startTime":0,"videoId":"{stream_id}","brand":"{brand}","genre":[]}}'

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
    return u''

def get_config_tag(url):
    global config_tag
    if not config_tag and xbmcvfs.exists(tag_file_path):
        tag_file = xbmcvfs.File(tag_file_path)
        config_tag = json.load(tag_file)
        tag_file.close()
    if url in config_tag:
        return config_tag[url]
    return u''

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
