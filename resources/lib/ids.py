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

user_agent = u'okhttp/4.3.1'
video_useragent = u'vvs-native-android/5.18.1-AOS-518017685 (Linux;Android 7.1.1) ExoPlayerLib/2.11.5'
#Joyn-Client-Version: 5.10.0-AOS-510006964
# from app
middleware_token = u'1ec991118fe49ca44c185ee6a86354ef'

joyn_version = u'5.18.1-AOS-518017685'
joyn_update_url = u'https://config.prd.platform.s.seventv.com/config/appConfig/AOS/5.18.1'

proxy_api_urls = [
    u'https://gimmeproxy.com/api/getProxy?post=true&country=DE&supportsHttps=true&anonymityLevel=1&protocol=http',
    u'https://api.getproxylist.com/proxy?anonymity[]=high%20anonymity&anonymity[]=anonymous&country[]=DE&allowsHttps=1&protocol[]=http',
    u'https://www.freshproxies.net/ProxyList?countries_1=DE&countries_2=DE&protocol=HTTPS&level=anon&order=uptime&frame=1H&format=json&fields=comp&key=',
    u'http://pubproxy.com/api/proxy?format=json&https=true&post=true&country=DE&level=anonymous,elite&type=http&limit=5']

# from https://psf.player.v0.maxdome.cloud/dist/playback-source-fetcher.min.js
xxtea_key = u'5C7838365C7864665C786638265C783064595C783935245C7865395C7838323F5C7866333D3B5C78386635'

base_url = u'https://api.joyn.de/graphql?'
post_request = u'{{"variables":{{{variables}}},"query":"{query}"}}'
post_url = u'https://api.joyn.de/graphql?enable_plus=true'
offset = 1000

# fragments for different things

MovieCoverFragment = u'fragment MovieCoverFragment on Movie{__typename id title copyrights markings startsAt endsAt description tagline licenseTypes productionYear productPlacement brands{__typename id title logo{__typename url}}genres{__typename name}images{__typename type url}video{__typename id duration licenses{__typename startDate endDate type}}ageRating{__typename description minAge ratingSystem}tracking{__typename agofCode externalAssetId brand}}'

SeriesCoverFragment = u'fragment SeriesCoverFragment on Series{__typename id copyrights markings title tagline numberOfSeasons description licenseTypes brands{__typename id title logo{__typename url}}images{__typename type url}ageRating{__typename description minAge ratingSystem}genres{__typename name}seasons@include(if: $withSeasons){__typename id number numberOfEpisodes}}'

BrandCoverFragment = u'fragment BrandCoverFragment on Brand{__typename id title path logo{__typename type url}livestream{__typename id quality}}'
BrandCoverFragmentEpg = u'fragment BrandCoverFragmentEpg on Brand{__typename id livestream{__typename id title quality eventStream gracenoteId liveStreamGroups epg(first: $first, offset: $offset){__typename id startDate endDate title secondaryTitle images{__typename id accentColor type url}}}logo{__typename accentColor url}hasVodContent title}'
 
EpisodeCoverFragment = u'fragment EpisodeCoverFragment on Episode{__typename id title number endsAt airdate markings description season{__typename number id numberOfEpisodes}images{__typename id copyright type url accentColor}video{__typename id duration quality licenses{__typename startDate endDate type}}series{__typename id copyrights ageRating{__typename description minAge ratingSystem}images{__typename url type}title tagline description genres{__typename name}licenseTypes}brands{__typename id title logo{__typename url}}ageRating{__typename description minAge ratingSystem}genres{__typename name type}licenseTypes tracking{__typename agofCode externalAssetId brand}preview productPlacement}'
 
EpgFragment = u'fragment EpgFragment on EpgEntry{__typename id startDate endDate images{__typename type url}title secondaryTitle livestream{__typename id markings brand{__typename id logo{__typename url accentColor}title}gracenoteId}}'
 
CompilationCoverFragment = u'fragment CompilationCoverFragment on Compilation{__typename id copyrights brands{__typename id title logo{__typename url}}images{__typename type url}title numberOfItems path ageRating{__typename description minAge ratingSystem}tagline description genres{__typename name type} licenseTypes}'

CompilationItemCoverFragment = u'fragment CompilationItemCoverFragment on CompilationItem{__typename id ageRating{__typename description minAge ratingSystem} compilation{__typename copyrights id title brands{__typename id logo{__typename url}title livestream{__typename id agofCode title quality}}path images{__typename accentColor type url}ageRating{__typename description minAge ratingSystem}}description endsAt genres{__typename name type}images{__typename accentColor type url}path startsAt title video{__typename id duration licenses{__typename startDate endDate type}}tracking{__typename agofCode externalAssetId brand}licenseTypes}'

TeaserCoverFragment = u'fragment TeaserCoverFragment on Teaser{__typename id title description relatedPathText relatedPath path information keywords teaserImages: images{__typename type url}teaserStartDate: startDate teaserEndDate: endDate teaserBrands: brands{__typename id livestream{__typename id liveStreamGroups agofCode title quality markings}logo{__typename accentColor url}hasVodContent title}}'

GenreItemCoverFragment = u'fragment GenreItemCoverFragment on GenreItem{__typename id title accentColor image{__typename type url}path}'

SportsMatchCoverFragment = u'fragment SportsMatchCoverFragment on SportsMatch{__typename id title description markings licenseTypes ageRating{__typename minAge ratingSystem description}tracking{__typename agofCode externalAssetId brand}brands{__typename id title logo{__typename type url}}images{__typename type url}video{__typename id licenses{__typename type startDate endDate}duration}startsAt endsAt path sports{__typename id title}sportsCompetition{__typename id title description}sportsStage{__typename id title sports{__typename id title path icon{__typename type url}}}}'

# requests
page_variables = u'"path":"{page_path}"'
overview_variables = u'"path":"/"'
overview_query = u'query LandingPage($path: String!){page(path: $path){__typename ... on LandingPage{blocks{__typename id anchorId isPersonalized ... on StandardLane{headline}... on FeaturedLane{headline}... on HighlightLane{headline}... on LiveLane{headline}... on ResumeLane{headline}... on ChannelLane{headline}... on BookmarkLane{headline}... on GenreLane{headline}... on CollectionLane{headline}... on RecoForYouLane{headline}... on TeaserLane{headline}}}}}'

livestream_variables = u'"first":2,"liveStreamGroupFilter":"DEFAULT","brandVisibilityFilter":"ALL"'
livestream_query = u'query getEpgNew($first: Int!, $offset: Int!=0, $liveStreamGroupFilter: LiveStreamGroupFilter!, $brandVisibilityFilter: BrandVisibilityFilter!){brands(hasLivestream: true, liveStreamGroupFilter: $liveStreamGroupFilter, visibilityFilter: $brandVisibilityFilter){...BrandCoverFragmentEpg}}' + BrandCoverFragmentEpg

epg_variables = u'"first":25, "offset":{offset}, "brandId":{brandId}'
epg_query = u'query getEpg($first: Int!, $offset: Int!, $brandId: ID!){brand(id: $brandId){...BrandCoverFragmentEpg}}' + BrandCoverFragmentEpg

fetch_variables = u'"blockId":"{blockId}","offset":{offset},"first":1000'
fetch_query = u'query SingleBlockQuery($blockId: String!, $offset: Int!, $first: Int!, $withSeasons: Boolean! = false){block(id: $blockId){__typename id assets(offset: $offset, first: $first){__typename ...MovieCoverFragment ...SeriesCoverFragment ...BrandCoverFragment ...EpisodeCoverFragment ...EpgFragment ...CompilationCoverFragment ...TeaserCoverFragment ...GenreItemCoverFragment ...SportsMatchCoverFragment}}}fragment EpgFragment on EpgEntry{__typename id startDate endDate images{__typename type url}title secondaryTitle livestream{__typename id markings brand{__typename id logo{__typename url accentColor}title}gracenoteId}}fragment TeaserCoverFragment on Teaser{__typename id title description relatedPathText relatedPath path information keywords teaserImages: images{__typename type url}teaserStartDate: startDate teaserEndDate: endDate teaserBrands: brands{__typename id livestream{__typename id liveStreamGroups agofCode title quality markings}logo{__typename accentColor url}hasVodContent title}}fragment GenreItemCoverFragment on GenreItem{__typename id title accentColor image{__typename type url}path}' + EpisodeCoverFragment + MovieCoverFragment + SeriesCoverFragment + BrandCoverFragment + CompilationCoverFragment + SportsMatchCoverFragment

series_variables = u'"seriesId":"{seriesId}","withSeasons":true'
series_query = u'query getSeries($seriesId: ID!, $withSeasons: Boolean! = false){series(id: $seriesId){...SeriesCoverFragment}}' + SeriesCoverFragment

bonus_variables = u'"seriesId":"{seriesId}","first":1000,"offset":{offset}'
bonus_query = u'query getBonus($seriesId: ID!, $first: Int!, $offset: Int!){series(id: $seriesId){__typename id ageRating{__typename description minAge ratingSystem}extras(first: $first, offset: $offset){__typename id title video{__typename duration id}images{__typename id copyright type url accentColor}tracking{__typename agofCode externalAssetId brand url}}}}'

season_variables = u'"seasonId":"{seasonId}","first":1000,"offset":{offset}'
season_query = u'query getSeason($seasonId: ID!, $first: Int!, $offset: Int!){season(id: $seasonId){__typename number title episodes(first: $first, offset: $offset){...EpisodeCoverFragment}}}' + EpisodeCoverFragment

channel_variables = u'"path":"{channelpath}","offset":{offset},"first":1000'
channel_query = u'query PathPageQuery($path: String!, $offset: Int!, $first: Int!, $withSeasons: Boolean! = false){page(path: $path){__typename ... on ChannelPage{assets(offset: $offset, first: $first){__typename ...MovieCoverFragment ...SeriesCoverFragment ...EpisodeCoverFragment ...CompilationCoverFragment}}... on GenrePage{blocks{__typename assets(offset: $offset, first: $first){__typename ...MovieCoverFragment ...SeriesCoverFragment ...EpisodeCoverFragment ...CompilationCoverFragment}}}}}' + EpisodeCoverFragment + MovieCoverFragment + SeriesCoverFragment + CompilationCoverFragment

search_variables = u'"text":"{search}"'
search_query = u'query searchQuery($text: String!, $withSeasons: Boolean! = false){search(term: $text, first: 50){__typename results{__typename ...BrandCoverFragment ...SeriesCoverFragment ...MovieCoverFragment ...CompilationCoverFragment ...SportsMatchCoverFragment}}}' + MovieCoverFragment + SeriesCoverFragment + BrandCoverFragment + CompilationCoverFragment + SportsMatchCoverFragment

compilation_details_variables = u'"id":"{id}"'
compilation_details_query = u'query GetCompilationDetailsQuery($id: ID!){compilation(id: $id){...CompilationCoverFragment}}' + CompilationCoverFragment

compilation_items_variables = u'"id":"{id}","offset":{offset},"first":1000'
compilation_items_query = u'query GetCompilationItemsQuery($id: ID!, $offset: Int!, $first: Int!){compilation(id: $id){__typename compilationItems(first: $first, offset: $offset){...CompilationItemCoverFragment}}}' + CompilationItemCoverFragment

compilation_item_variables = u'"id":"{id}"'
compilation_item_query = u'query GetCompilationByIdQuery($id: ID!){compilationItem(id: $id){...CompilationItemCoverFragment}}' + CompilationItemCoverFragment

episode_variables = u'"episodeId":"{episodeId}"'
episode_query = u'query getEpisodeById($episodeId: ID!){episode(id: $episodeId){...EpisodeCoverFragment}}' + EpisodeCoverFragment
{"assetId":"b_p0w0mwktnzs","accentColorType":"DARK_VIBRANT"}
movie_variables = u'"movieId":"{id}"'
movie_query = u'query getMovie($movieId: ID!){movie(id: $movieId){...MovieCoverFragment}}' + MovieCoverFragment

sport_match_variables = u'"assetId":"{id}"'
sport_match_query = u'query getSportsMatch($assetId: ID!){sportsMatch(id: $assetId){...SportsMatchCoverFragment}}' + SportsMatchCoverFragment

recommendation_variables = u'"id":"{id}"'
recommendation_query = u'query getRecommendationsForAsset($id: ID!, $withSeasons: Boolean! = false){recommendationForAsset(assetId: $id){__typename recoCorrelationId assets{__typename ...SeriesCoverFragment ...MovieCoverFragment ...CompilationCoverFragment}}}' + SeriesCoverFragment + MovieCoverFragment + CompilationCoverFragment

image_url = u'{0}/profile:original'

player_config_url = u'https://playerconfig.prd.platform.s.joyn.de/df0aba535c694114d8e2b193b9affd97.json'

psf_config_url = u'https://psf.player.v0.maxdome.cloud/config/psf.json'

entitlement_token_legacy_url = u'entitlement-token/anonymous'


auth_key_url = u'https://auth.joyn.de/auth/anonymous'
auth_key_request = u'{{"client_id":"{uuid_no_hyphen}","client_name":"Kodi"}}'

auth_key_refresh_url = u'https://auth.joyn.de/auth/refresh'
auth_key_refresh_request = u'{{"refresh_token":"{refresh_token}","client_id":"{uuid_no_hyphen}","client_name":"Kodi"}}'

entitlement_token_url = u'entitlement-token'
entitlement_token_header = 'Authorization'
entitlement_token_header_format = u'{token_type} {token}'

nuggvars_url = u'https://71iapp-cp.nuggad.net/rc?nuggn=2011964291&nuggsid=1282618500&nuggtg=TV_DRAMA,EDITORIAL_CONT_VIDEO&tok='

video_playback_url = u'playout/video/{episode_id}?entitlement_token={entitlement_token}&clientData={clientData}&sig={sig}'
live_playback_url = u'playout/channel/{stream_id}?entitlement_token={entitlement_token}&clientData={clientData}&sig={sig}'

clientdata = u'{{"idfa":"","noAdCooldown":true,"npa":false,"nuggvars":"{nuggvars}","ppid":"","startTime":0,"videoId":"{episode_id}","duration":{duration},"brand":"{brand}","genre":[],"tvshowid":"{tvshow_id}"}}'

#clientdata = u'{{"idfa":"c363b386-e2b0-4e0e-b5fd-11d51a7e5be8","noAdCooldown":false,"npa":false,"ppid":"1112d5f24aa54935bcc338722e47e50f","segment":{{"channel":"mobile","type":"track","messageId":"84cb0b08-b63a-408b-8e2b-2ff05fee9b46","timestamp":"2020-09-04T15:22:39.194Z","context":{{"app":{{"build":"510006964","name":"Joyn","namespace":"de.prosiebensat1digital.seventv","version":"5.10.0-AOS-510006964"}},"traits":{{"anonymousId":"0a840bac-5ac7-4c64-b2ac-725ac231e514","user_status":"logged in","profile_id":"JNDE-2c1fcb4c-b464-49b8-a1ed-eac4135b98a8_cc0ec17f71f60ac3","device_type":"phone","device_os":"android","userId":"JNDE-2c1fcb4c-b464-49b8-a1ed-eac4135b98a8"}},"os":{{"name":"Android","version":"5.1.1"}},"timezone":"Africa/Harare","screen":{{"density":1.5,"width":1280,"height":720}},"session_id":"1599232938705","userAgent":"Dalvik/2.1.0 (Linux; U; Android 5.1.1; SM-N950N Build/NMF26X)","locale":"de-DE","network":{{"wifi":true,"carrier":"","bluetooth":false,"cellular":false}},"environment":"production","library":{{"name":"analytics-android","version":"4.5.0"}},"protocols_schema_version":"1","device":{{"id":"00d8617075a93122","manufacturer":"samsung","model":"SM-N950N","name":"greatlteks","advertisingId":"c363b386-e2b0-4e0e-b5fd-11d51a7e5be8","adTrackingEnabled":true}}}},"integrations":{{}},"userId":"JNDE-2c1fcb4c-b464-49b8-a1ed-eac4135b98a8","anonymousId":"0a840bac-5ac7-4c64-b2ac-725ac231e514","event":"Video Playback Requested","properties":{{"asset_id":"b_pq2sgspq3ab","asset_type":"movie","asset_title":"no game no life: zero","asset_season":-1,"asset_episode":-1,"asset_genre":"action, abenteuer, anime","asset_channel_name":"prosieben maxx","asset_episode_id":"a_pq2sgsppxhz","asset_length":6159,"asset_position":0,"asset_license_type":"avod, unknown","list_name":"detailhero","list_position":1,"list_type":"detailhero","list_length":1,"screen_name":"movies"}}}},"startTime":0,"country":"de","videoId":"{episode_id}","duration":{duration},"brand":"{brand}","genre":[],"tvshowid":"{tvshow_id}"}}'

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
