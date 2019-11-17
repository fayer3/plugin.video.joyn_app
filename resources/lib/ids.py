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

user_agent = u'okhttp/3.14.3'
video_useragent = u'vvs-native-android/4.0.0.400004218 (Linux;Android 5.1.1) ExoPlayerLib/2.10.0'

# from app
middleware_token = u'1ec991118fe49ca44c185ee6a86354ef'

joyn_version = u'400004217'

# from https://psf.player.v0.maxdome.cloud/dist/playback-source-fetcher.min.js
xxtea_key = u'5C7838365C7864665C786638265C783064595C783935245C7865395C7838323F5C7866333D3B5C78386635'

base_url_mid = u'https://middleware.p7s1.io/joyn/v1/'
base_url = u'https://api.joyn.de/graphql?'
variables = u'variables={0}'
operationName = u'operationName={0}'
extensions = u'extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22{0}%22%7D%7D'
offset = 1000

#overview_url = base_url + u'ui?path=/'
overview_url = u'{0}{1}&{2}&{3}'.format(base_url, variables.format(u'%7B%22path%22%3A%22%2F%22%7D'), operationName.format(u'LandingPage'), extensions.format(u'cd052ca5717f10d182d4735c60f478b4df74aab0228b25bd3bc2f52618e36d87'))
#livestream_url = 'https://middleware.p7s1.io/joyn/v1/brands?selection={data{id, channelId ,agofCodes,metadata}}&streamIds=true&mock=false'
#livestream_url = base_url + u'brands?selection=%7Bdata%7Bid%2C%20channelId%20%2CagofCodes%2Cmetadata%7D%7D&streamIds=true&mock=false'
#livestream_url = u'{0}{1}&{2}'.format(base_url, operationName.format(u'getBrands'), extensions.format(u'f760164a9ab41556f864211be2c7a06a817c6f52ee4a2ab12980dea45297d658'))
livestream_url = u'{0}{1}&{2}'.format(base_url, operationName.format(u'getEpg'), extensions.format(u'3edb47069dd26e3b8564df639faff9df815318e95d54c89ff2577ab3128e613b'))

#https://middleware.p7s1.io/joyn/v1/epg?selection={totalCount,data{id,title,description,tvShow,type,productionYear,tvChannelName,channelId,startTime,endTime,repeatTime,video,genres{type,title},images(subType:"cover,logo,art_direction"){url,subType}}}&skip=0&limit=1000&from={0}&to={1}&sortBy=startTime&sortAscending=true'
epg_url = base_url_mid + u'epg?selection=%7BtotalCount%2Cdata%7Bid%2Ctitle%2Cdescription%2CtvShow%2Ctype%2CproductionYear%2CtvChannelName%2CchannelId%2CstartTime%2CendTime%2CrepeatTime%2Cvideo%2Cgenres%7Btype%2Ctitle%7D%2Cimages%28subType%3A%22cover%2Clogo%2Cart_direction%22%29%7Burl%2CsubType%7D%7D%7D&skip=0&limit=1000&from={0}&to={1}&sortBy=startTime&sortAscending=true'

epg_now_url = base_url_mid + u'epg/now?selection=%7BtotalCount%2Cdata%7Bid%2Ctitle%2Cdescription%2CtvShow%2Ctype%2CproductionYear%2CtvChannelName%2CchannelId%2CstartTime%2CendTime%2CrepeatTime%2Cvideo%2Cgenres%7Btype%2Ctitle%7D%2Cimages%28subType%3A%22cover%2Clogo%2Cart_direction%22%29%7Burl%2CsubType%7D%7D%7D&skip=0&limit=5000&sortAscending=true'

epg_channel_url = base_url_mid + u'epg?selection=%7BtotalCount%2Cdata%7Bid%2Ctitle%2Cdescription%2CtvShow%2Ctype%2CproductionYear%2CtvChannelName%2CchannelId%2CstartTime%2CendTime%2CrepeatTime%2Cvideo%2Cgenres%7Btype%2Ctitle%7D%2Cimages%28subType%3A%22cover%2Clogo%2Cart_direction%22%29%7Burl%2CsubType%7D%7D%7D&skip=0&limit=1000&sortBy=startTime&sortAscending=true&channelId={channel}'

#fetch_url = base_url + u'fetch/{0}'
#fetch_selection = 'selection={data{id,visibilities, channelId ,agofCodes,duration,metadata{de}}}'
#fetch_selection = u'selection=%7Bdata%7Bid%2Cvisibilities%2C%20channelId%20%2CagofCodes%2Cduration%2Cmetadata%7Bde%7D%7D%7D'
fetch_url = u'{0}{1}&{2}&{3}'.format(base_url, variables.format(u'%7B%22blockId%22%3A%22{blockId}%22%2C%22offset%22%3A{offset}%2C%22first%22%3A1000%7D'), operationName.format(u'SingleBlockQuery'), extensions.format(u'ff72dbd65203a42871330a5b09c8df21aa7051a3682759f8c0072e782c96bd20'))

#seasons_url = base_url + u'seasons?tvShowId={0}&subType=Hauptfilm&sortBy=seasonsOrder&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D&sortAscending=true'
#seasons_selection = '&subType=Hauptfilm&sortBy=seasonsOrder&selection={data{id,channelId,visibilities,duration,metadata{de}}}&sortAscending=true'
series_url = u'{0}{1}&{2}&{3}'.format(base_url, variables.format(u'%7B%22seriesId%22%3A%22{seriesId}%22%2C%22includeBookmark%22%3Afalse%7D'), operationName.format(u'getSeries'), extensions.format(u'6c5478b6d674a55b131f90443eedbea2479b43975764f9efc86eb21216a4bfb3'))

bonus_url = u'{0}{1}&{2}&{3}'.format(base_url, variables.format(u'%7B%22seriesId%22%3A%22{seriesId}%22%2C%22first%22%3A5000%2C%22offset%22%3A{offset}%7D'), operationName.format(u'getBonus'), extensions.format(u'2f90cee0784231857b38f11785194fa0579cb2aabca1dd35dc4ecefe1d4830fa'))

#season_url = base_url + u'videos?seasonId={0}&sortBy=seasonsOrder&sortAscending=true&skip=0&subType=Hauptfilm&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2CtvShow%2Cmetadata%7Bde%7D%7D%7D'
#season_selection = '&sortBy=seasonsOrder&sortAscending=true&skip=0&subType=Hauptfilm&selection={data{id,channelId,visibilities,duration,metadata{de}}}'
season_url = u'{0}{1}&{2}&{3}'.format(base_url, variables.format(u'%7B%22seasonId%22%3A%22{seasonId}%22%2C%22first%22%3A1000%2C%22offset%22%3A{offset}%7D'), operationName.format(u'getSeason'), extensions.format(u'3bbd1e1cc8ffbc7215e14a834684168c25816424886bbde7e9ad0e5b741447d6'))

season_post_custom = u'{{"variables":{{"seasonId":"{seasonId}","first":1000,"offset":{offset}}},"query":"query getSeason($seasonId: ID!, $first: Int!, $offset: Int!) {{ season(id: $seasonId) {{ __typename number title episodes(first: $first, offset: $offset) {{__typename id number description images {{__typename id copyright type url accentColor}} series {{__typename ageRating {{__typename label minAge ratingSystem}} images {{__typename accentColor url type}}}} endsAt airdate title video {{__typename id duration licenses {{__typename startDate endDate type}}}} brands {{__typename id title}} season {{__typename number id numberOfEpisodes}} genres {{__typename name type}} tracking {{__typename primaryAirdateBrand agofCode trackingId visibilityStart brand}}}}}}}}"}}'

#tvshow_url = base_url + u'tvshows?ids={0}&limit=1&subType=Hauptfilm&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D&filter=visible&type=tvShow'
#tvshow_selection = '&limit=1&subType=Hauptfilm&selection={data{id,channelId,visibilities,duration,metadata{de}}}&filter=visible&type=tvShow'

#channel_url = base_url + u'tvshows?skip={0}&limit=5000&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D&filter=visible&type=tvShow%2Cmovie&channelId={1}'
#channel_limit = 5000
channel_url = u'{0}{1}&{2}&{3}'.format(base_url, variables.format(u'%7B%22path%22%3A%22{channelpath}%22%2C%22offset%22%3A{offset}%2C%22first%22%3A1000%7D'), operationName.format(u'ChannelPageQuery'), extensions.format(u'8be0f484d27bc21f50308c7eb5ede43bdaf06acb045ca1555a369a37c17a65ae'))

#search_tvshow_url = base_url + u'tvshows?search={0}&limit=5000&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D&filter=visible&type=tvShow'
#search_movie_url = base_url + u'tvshows?search={0}&limit=5000&subType=Hauptfilm&selection=%7Bdata%7Bid%2CchannelId%2Cvisibilities%2Cduration%2Cmetadata%7Bde%7D%7D%7D&filter=visible&type=movie'
#search_limit = 5000
search_url = u'{0}{1}&{2}&{3}'.format(base_url, variables.format(u'%7B%22text%22%3A%22{search}%22%7D'), operationName.format(u'searchQuery'), extensions.format(u'b3924f833195f871048812798249fef1b202b9829f070456e9a1cbbab2981d0d'))

compilation_details_url = u'{0}{1}&{2}&{3}'.format(base_url, variables.format(u'%7B%22id%22%3A%22{id}%22%2C%22includeBookmark%22%3Atrue%7D'), operationName.format(u'GetCompilationDetailsQuery'), extensions.format(u'77ab6c2cc89ab434a2e73f7e254455f67a4bb4a9b22b72d53c0710e3f8cebacc'))

compilation_details_post = u'{{"operationName":"GetCompilationDetailsQuery","variables":{{"id":"{id}"}},"query":"query GetCompilationDetailsQuery($id: ID!) {{ compilation(id: $id) {{ __typename id description images {{ __typename id accentColor type url }} genres {{ __typename name type }} brands {{ __typename id logo {{ __typename id url accentColor }} title }} title ageRating {{ __typename label minAge ratingSystem }} copyrights numberOfItems nextCompilationItem {{ __typename ... on CompilationItem {{ ...CompilationItemCoverFragment }} }} }}}}fragment CompilationItemCoverFragment on CompilationItem {{ __typename id compilation {{ __typename id title brands {{ __typename id logo {{ __typename url }} title }} path images {{ __typename accentColor type url }} ageRating {{ __typename label minAge ratingSystem }} }} description endsAt genres {{ __typename name type }} images {{ __typename accentColor type url }} path resumePosition {{ __typename position }} startsAt title video {{ __typename id duration licenses {{ __typename startDate endDate type }} }} tracking {{ __typename primaryAirdateBrand agofCode trackingId visibilityStart brand }}}}"}}'

compilation_items_url = u'{0}{1}&{2}&{3}'.format(base_url, variables.format(u'%7B%22id%22%3A%22{id}%22%2C%22offset%22%3A{offset}%2C%22first%22%3A1000%7D'), operationName.format(u'GetCompilationItemsQuery'), extensions.format(u'a9ca81946b994ff76c1ad337b1399e128125c16615af9b2e36a3b50e3ddf6060'))

compilation_items_post = u'{{"operationName":"GetCompilationItemsQuery","variables":{{"id":"{id}","offset":{offset},"first":1000}},"query":"query GetCompilationItemsQuery($id: ID!, $offset: Int!, $first: Int!) {{ compilation(id: $id) {{ __typename compilationItems(first: $first, offset: $offset) {{ __typename ... on CompilationItem {{ ...CompilationItemCoverFragment }} }} }}}}fragment CompilationItemCoverFragment on CompilationItem {{ __typename id compilation {{ __typename id title brands {{ __typename id logo {{ __typename url }} title }} path images {{ __typename accentColor type url }} ageRating {{ __typename label minAge ratingSystem }} }} description endsAt genres {{ __typename name type }} images {{ __typename accentColor type url }} path resumePosition {{ __typename position }} startsAt title video {{ __typename id duration licenses {{ __typename startDate endDate type }} }} tracking {{ __typename primaryAirdateBrand agofCode trackingId visibilityStart brand }}}}"}}'

compilation_item_url = u'{0}{1}&{2}&{3}'.format(base_url, variables.format(u'%7B%22id%22%3A%22{id}%22%7D'), operationName.format(u'GetCompilationByIdQuery'), extensions.format(u'22c17acfea3694b121a5ca953a784274727dce02abe538742420ae94169030b6'))

compilation_item_post = u'{{"operationName":"GetCompilationByIdQuery","variables":{{"id":"{id}"}},"query":"query GetCompilationByIdQuery($id: ID!) {{ compilationItem(id: $id) {{ __typename id compilation {{ __typename id title brands {{ __typename id logo {{ __typename url }} title }} path images {{ __typename accentColor type url }} ageRating {{ __typename label minAge ratingSystem }} }} description endsAt genres {{ __typename name type }} images {{ __typename accentColor type url }} path resumePosition {{ __typename position }} startsAt title video {{ __typename id duration licenses {{ __typename startDate endDate type }} }} tracking {{ __typename primaryAirdateBrand agofCode trackingId visibilityStart brand }} }}}}"}}'

episode_url = u'{0}{1}&{2}&{3}'.format(base_url, variables.format(u'%7B%22episodeId%22%3A%22{episodeId}%22%7D'), operationName.format(u'getEpisodeById'), extensions.format(u'666308ff8ce0bd1340d41131564a585a5a624ae9ccb749325b883f00d6bc4a39'))

#video_info_url = base_url_mid + u'metadata/video/{0}?country=de&devicetype=phone&recommendations=2'

image_url = u'{0}/profile:original'

player_config_url = u'https://playerconfig.prd.platform.s.joyn.de/df0aba535c694114d8e2b193b9affd97.json'

psf_config_url = u'https://psf.player.v0.maxdome.cloud/config/psf.json'

entitlement_token_url = u'entitlement-token/anonymous'

nuggvars_url = u'https://71iapp-cp.nuggad.net/rc?nuggn=2011964291&nuggsid=1282618500&nuggtg=TV_DRAMA,EDITORIAL_CONT_VIDEO&tok='

video_playback_url = u'playout/video/{episode_id}?entitlement_token={entitlement_token}&clientData={clientData}&sig={sig}'
live_playback_url = u'playout/channel/{stream_id}?entitlement_token={entitlement_token}&clientData={clientData}&sig={sig}'

clientdata = u'{{"idfa":"","noAdCooldown":true,"npa":false,"nuggvars":"{nuggvars}","ppid":"","startTime":0,"videoId":"{episode_id}","duration":{duration},"brand":"{brand}","genre":[],"tvshowid":"{tvshow_id}"}}'

clientdata_live = u'{{"idfa":"","noAdCooldown":true,"npa":false,"nuggvars":"0","ppid":"","startTime":0,"videoId":"{stream_id}","brand":"{brand}","genre":[]}}'

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
