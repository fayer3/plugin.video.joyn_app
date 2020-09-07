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
video_useragent = u'vvs-native-android/5.10.0-AOS-510006964 (Linux;Android 7.1.1) ExoPlayerLib/2.11.5'
#Joyn-Client-Version: 5.10.0-AOS-510006964
# from app
middleware_token = u'1ec991118fe49ca44c185ee6a86354ef'

joyn_version = u'5.10.0-AOS-510006964'
joyn_update_url = u'https://config.prd.platform.s.seventv.com/config/appConfig/AOS/5.10.0'

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

overview_variables = u'"path":"/"'
overview_query = u'query LandingPage($path: String!){page(path: $path){__typename ... on LandingPage{blocks{__typename id anchorId isPersonalized ... on StandardLane{headline}... on FeaturedLane{headline}... on LiveLane{headline}... on ResumeLane{headline}... on ChannelLane{headline}... on BookmarkLane{headline}... on GenreLane{headline}}}}}'

livestream_variables = u'"first":2'
livestream_query = u'query getEpg($first: Int!){brands{__typename id livestream{__typename id title quality epg(first: $first){__typename id startDate endDate title secondaryTitle images{__typename id accentColor type url}}}logo{__typename accentColor url}hasVodContent title}}'

epg_variables = u'"first":25, "offset":{offset}, "brandId":{brandId}'
epg_query = u'query getEpg($first: Int!, $offset: Int!, $brandId: ID!){brand(id: $brandId){__typename id livestream{__typename id title quality epg(first: $first, offset: $offset){__typename id startDate endDate title secondaryTitle images{__typename id accentColor type url}}}logo{__typename accentColor url}hasVodContent title}}'

fetch_variables = u'"blockId":"{blockId}","offset":{offset},"first":1000'
fetch_query = u'query SingleBlockQuery($blockId: String!, $offset: Int!, $first: Int!){block(id: $blockId){__typename id assets(offset: $offset, first: $first){__typename ...ResumeMovieCoverFragment ...SeriesCoverFragment ...BrandCoverFragment ...EpisodeCoverFragment ...EpgFragment ...CompilationCoverFragment ...GenreItemCoverFragment}... on HeroLane{heroLaneAssets: assets{__typename ... on Series{id}... on Movie{id}... on Compilation{id}}}... on UpsellingLane{id teasers{__typename id title relatedPath description relatedPathText images{__typename id type accentColor url}information}}}}fragment ResumeMovieCoverFragment on Movie{__typename id markings startsAt endsAt brands{__typename id title logo{__typename url}}images{__typename accentColor type url}title tagline video{__typename id duration}description copyrights genres{__typename name}licenseTypes ageRating{__typename description minAge ratingSystem}tracking{__typename agofCode externalAssetId brand}}fragment SeriesCoverFragment on Series{__typename id markings brands{__typename id title logo{__typename url}}images{__typename accentColor type url}ageRating{__typename description minAge ratingSystem}title tagline numberOfSeasons description copyrights genres{__typename name}licenseTypes}fragment BrandCoverFragment on Brand{__typename id title path logo{__typename type accentColor url}livestream{__typename id quality}}fragment EpisodeCoverFragment on Episode{__typename id title number endsAt markings season{__typename number}video{__typename id duration quality licenses{__typename startDate endDate type}}series{__typename id copyrights images{__typename accentColor url type}brands{__typename id title logo{__typename url}}title tagline description genres{__typename name}licenseTypes ageRating{__typename description minAge ratingSystem}}genres{__typename name type}licenseTypes tracking{__typename agofCode externalAssetId brand}}fragment EpgFragment on EpgEntry{__typename id startDate endDate images{__typename type url accentColor}title secondaryTitle livestream{__typename id brand{__typename id logo{__typename url accentColor}title}}}fragment CompilationCoverFragment on Compilation{__typename id brands{__typename id title logo{__typename url}}images{__typename accentColor type url}title numberOfItems path ageRating{__typename description minAge ratingSystem}tagline description copyrights genres{__typename name type}}fragment GenreItemCoverFragment on GenreItem{__typename id title image{__typename accentColor type url}path}'

series_variables = u'"seriesId":"{seriesId}","isUserLoggedIn":false'
series_query = u'query getSeries($seriesId: ID!, $isUserLoggedIn: Boolean!){series(id: $seriesId){__typename id title description markings images{__typename type url accentColor}numberOfSeasons brands{__typename id logo{__typename id url accentColor}title}trailer{__typename id title images{__typename id url}video{__typename id duration}} seasons{__typename id number numberOfEpisodes}copyrights genres{__typename name type}ageRating{__typename description minAge ratingSystem}copyrights tagline licenseTypes isBookmarked @include(if: $isUserLoggedIn) }}'

bonus_variables = u'"seriesId":"{seriesId}","first":1000,"offset":{offset}'
bonus_query = u'query getBonus($seriesId: ID!, $first: Int!, $offset: Int!){series(id: $seriesId){__typename id ageRating{__typename description minAge ratingSystem}extras(first: $first, offset: $offset){__typename id title video{__typename duration id}images{__typename id copyright type url accentColor}tracking{__typename agofCode externalAssetId brand url}}}}'

season_variables = u'"seasonId":"{seasonId}","first":1000,"offset":{offset}'
season_query = u'query getSeason($seasonId: ID!, $first: Int!, $offset: Int!){season(id: $seasonId){__typename number title episodes(first: $first, offset: $offset){__typename id ageRating{__typename description minAge ratingSystem} number markings description images{__typename id copyright type url accentColor}series{__typename copyrights ageRating{__typename description minAge ratingSystem}images{__typename accentColor url type}title}endsAt airdate title video{__typename id duration licenses{__typename startDate endDate type}}brands{__typename id title logo{__typename url}}season{__typename number id numberOfEpisodes}genres{__typename name type}licenseTypes tracking{__typename agofCode externalAssetId brand}}}}'

channel_variables = u'"path":"{channelpath}","offset":{offset},"first":1000'
channel_query = u'query PathPageQuery($path: String!, $offset: Int!, $first: Int!){page(path: $path){__typename ... on ChannelPage{assets(offset: $offset, first: $first){__typename ...ResumeMovieCoverFragment ...SeriesCoverFragment ...EpisodeCoverFragment ...CompilationCoverFragment}}... on GenrePage{blocks{__typename assets(offset: $offset, first: $first){__typename ...ResumeMovieCoverFragment ...SeriesCoverFragment ...EpisodeCoverFragment ...CompilationCoverFragment}}}}}fragment ResumeMovieCoverFragment on Movie{__typename id markings startsAt endsAt brands{__typename id title logo{__typename url}}images{__typename accentColor type url}title tagline video{__typename id duration}description copyrights genres{__typename name}licenseTypes ageRating{__typename description minAge ratingSystem}tracking{__typename agofCode externalAssetId brand}}fragment SeriesCoverFragment on Series{__typename id copyrights markings brands{__typename id title logo{__typename url}}images{__typename accentColor type url}ageRating{__typename description minAge ratingSystem}title tagline numberOfSeasons description genres{__typename name}licenseTypes}fragment EpisodeCoverFragment on Episode{__typename id title number endsAt markings season{__typename number}video{__typename id duration quality licenses{__typename startDate endDate type}}series{__typename id copyrights images{__typename accentColor url type}brands{__typename id title logo{__typename url}}title tagline description genres{__typename name}licenseTypes ageRating{__typename description minAge ratingSystem}}genres{__typename name type}licenseTypes tracking{__typename agofCode externalAssetId brand}}fragment CompilationCoverFragment on Compilation{__typename id copyrights brands{__typename id title logo{__typename url}}images{__typename accentColor type url}title numberOfItems path ageRating{__typename description minAge ratingSystem}tagline description genres{__typename name type}}'

search_variables = u'"text":"{search}"'
search_query = u'query searchQuery($text: String!){search(term: $text, first: 50){__typename results{__typename ...BrandCoverFragment ...SeriesCoverFragment ...MovieCoverFragment ...CompilationCoverFragment}}}fragment BrandCoverFragment on Brand{__typename id title path logo{__typename type accentColor url}livestream{__typename id quality}}fragment SeriesCoverFragment on Series{__typename id copyrights markings brands{__typename id title logo{__typename url}}images{__typename accentColor type url}ageRating{__typename description minAge ratingSystem}title tagline numberOfSeasons description genres{__typename name}licenseTypes}fragment MovieCoverFragment on Movie{__typename id copyrights markings startsAt endsAt brands{__typename id title logo{__typename url}}images{__typename accentColor type url}title tagline video{__typename id duration}description genres{__typename name}licenseTypes ageRating{__typename description minAge ratingSystem}tracking{__typename agofCode externalAssetId brand}}fragment CompilationCoverFragment on Compilation{__typename id copyrights brands{__typename id title logo{__typename url}}images{__typename accentColor type url}title numberOfItems path ageRating{__typename description minAge ratingSystem}tagline description genres{__typename name type}}'

compilation_details_variables = u'"id":"{id}","includeBookmark":false'
compilation_details_query = u'query GetCompilationDetailsQuery($id: ID!, $includeBookmark: Boolean!){compilation(id: $id){__typename id copyrights description images{__typename id accentColor type url}genres{__typename name type}brands{__typename id logo{__typename id url accentColor}title}title ageRating{__typename description minAge ratingSystem}copyrights numberOfItems isBookmarked @include(if: $includeBookmark)}}fragment CompilationItemCoverFragment on CompilationItem{__typename id compilation{__typename id title brands{__typename id logo{__typename url}title livestream{__typename id agofCode title quality}}path images{__typename accentColor type url}ageRating{__typename description minAge ratingSystem}}description endsAt genres{__typename name type}images{__typename accentColor type url}path startsAt title video{__typename id duration licenses{__typename startDate endDate type}}tracking{__typename agofCode externalAssetId brand}}'

compilation_items_variables = u'"id":"{id}","offset":{offset},"first":1000'
compilation_items_query = u'query GetCompilationItemsQuery($id: ID!, $offset: Int!, $first: Int!){compilation(id: $id){__typename compilationItems(first: $first, offset: $offset){__typename ... on CompilationItem{...CompilationItemCoverFragment}}}}fragment CompilationItemCoverFragment on CompilationItem{__typename id ageRating{__typename description minAge ratingSystem} compilation{__typename copyrights id title brands{__typename id logo{__typename url}title livestream{__typename id agofCode title quality}}path images{__typename accentColor type url}ageRating{__typename description minAge ratingSystem}}description endsAt genres{__typename name type}images{__typename accentColor type url}path startsAt title video{__typename id duration licenses{__typename startDate endDate type}}tracking{__typename agofCode externalAssetId brand}}'

compilation_item_variables = u'"id":"{id}"'
compilation_item_query = u'query GetCompilationByIdQuery($id: ID!){compilationItem(id: $id){__typename ageRating{__typename description minAge ratingSystem} id compilation{__typename id copyrights title brands{__typename id logo{__typename url}title livestream{__typename id agofCode title quality}}genres{__typename name type}path images{__typename accentColor type url}ageRating{__typename description minAge ratingSystem}}description endsAt genres{__typename name type}images{__typename accentColor type url}path startsAt title video{__typename id duration licenses{__typename startDate endDate type}}tracking{__typename agofCode externalAssetId brand}}}'

episode_variables = u'"episodeId":"{episodeId}"'
episode_query = u'query getEpisodeById($episodeId: ID!){episode(id: $episodeId){__typename ageRating{__typename description minAge ratingSystem} id number markings images{__typename id copyright type url accentColor}endsAt airdate title brands{__typename id title}video{__typename id duration licenses{__typename startDate endDate type}}season{__typename number id}series{__typename id copyrights title images{__typename type url accentColor}ageRating{__typename description minAge ratingSystem}licenseTypes tagline brands{__typename id logo{__typename url}title livestream{__typename id agofCode title quality}}genres{__typename name type}}genres{__typename name type}licenseTypes tracking{__typename agofCode externalAssetId brand}}}'

movie_variables = u'"movieId":"{id}","includeBookmark":false'
movie_query = u'query getMovie($movieId: ID!, $includeBookmark: Boolean!){movie(id: $movieId){__typename id title markings startsAt endsAt description genres{__typename type name}images{__typename url type accentColor}licenseTypes productionYear video{__typename id duration licenses{__typename startDate endDate type}}brands{__typename id logo{__typename id url accentColor}title livestream{__typename id agofCode title quality}}ageRating{__typename description minAge ratingSystem}copyrights tagline tracking{__typename agofCode externalAssetId brand}isBookmarked @include(if: $includeBookmark)}}'

recommendation_variables = u'"id":"{id}"'
recommendation_query = u'query getRecommendationsForAsset($id: ID!){recommendationForAsset(assetId: $id){__typename recoCorrelationId assets{__typename ...SeriesCoverFragment ...MovieCoverFragment}}}fragment SeriesCoverFragment on Series{__typename id copyrights markings brands{__typename id title logo{__typename url}}images{__typename accentColor type url}ageRating{__typename description minAge ratingSystem}title tagline numberOfSeasons description genres{__typename name}licenseTypes}fragment MovieCoverFragment on Movie{__typename id copyrights markings startsAt endsAt brands{__typename id title logo{__typename url}}images{__typename accentColor type url}title tagline video{__typename id duration}description genres{__typename name}licenseTypes ageRating{__typename description minAge ratingSystem}tracking{__typename agofCode externalAssetId brand}}'

image_url = u'{0}/profile:original'

player_config_url = u'https://playerconfig.prd.platform.s.joyn.de/df0aba535c694114d8e2b193b9affd97.json'

psf_config_url = u'https://psf.player.v0.maxdome.cloud/config/psf.json'

entitlement_token_legacy_url = u'entitlement-token/anonymous'


auth_key_url = u'https://auth.joyn.de/auth/anonymous'
auth_key_request = u'{{"client_id":"{uuid_no_hyphen}","client_name":"Kodi"}}'

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
