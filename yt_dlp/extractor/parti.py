
from .common import InfoExtractor
from ..utils import UserNotLive, int_or_none, parse_iso8601, url_or_none, urljoin
from ..utils.traversal import require, traverse_obj


class PartiBaseIE(InfoExtractor):
    def _call_api(self, path, video_id, note=None):
        return self._download_json(
            f'https://api-backend.parti.com/parti_v2/profile/{path}', video_id, note)


class PartiVideoIE(PartiBaseIE):
    IE_NAME = 'parti:video'
    _VALID_URL = r'https?://(?:www\.)?parti\.com/video/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://parti.com/video/66284',
            'info_dict': {
                'id': '66284',
                'ext': 'mp4',
                'title': 'NOW LIVE ',
                'upload_date': '20250327',
                'is_live': False,
                'categories': list,
                'thumbnail': 'https://assets.parti.com/351424_eb9e5250-2821-484a-9c5f-ca99aa666c87.png',
                'channel': 'ItZTMGG',
                'timestamp': 1743044379,
            },
            'params': {'skip_download': 'm3u8'},
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._call_api(f'get_livestream_channel_info/recent/{video_id}', video_id)
        formats = self._extract_m3u8_formats(
            urljoin('https://watch.parti.com', data['livestream_recording']), video_id, 'mp4')

        return {
            'id': video_id,
            'formats': formats,
            'is_live': False,
            **traverse_obj(data, {
                'title': ('event_title', {str}),
                'channel': ('user_name', {str}),
                'thumbnail': ('event_file', {url_or_none}),
                'categories': ('category_name', {str}, all),
                'timestamp': ('event_start_ts', {int_or_none}),
            }),
        }


class PartiLivestreamIE(PartiBaseIE):
    IE_NAME = 'parti:livestream'
    _VALID_URL = r'https?://(?:www\.)?parti\.com/creator/(?P<service>[\w]+)/(?P<id>[\w/-]+)'
    _TESTS = [
        {
            'url': 'https://parti.com/creator/parti/Capt_Robs_Adventures',
            'info_dict': {
                'id': 'Capt_Robs_Adventures',
                'ext': 'mp4',
                'title': str,
                'description': str,
                'upload_date': str,
                'is_live': True,
                'live_status': 'is_live',
            },
            'params': {'skip_download': 'm3u8'},
        },
        {
            'url': 'https://parti.com/creator/discord/sazboxgaming/0',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        service, creator_slug = self._match_valid_url(url).group('service', 'id')

        encoded_creator_slug = creator_slug.replace('/', '%23')
        creator_id = self._call_api(
            f'get_user_by_social_media/{service}/{encoded_creator_slug}',
            creator_slug, note='Fetching user ID')

        data = self._call_api(
            f'get_livestream_channel_info/{creator_id}', creator_id,
            note='Fetching user profile feed')['channel_info']

        if not traverse_obj(data, ('channel', 'is_live', {bool})):
            raise UserNotLive(video_id=creator_id)

        stream_data = traverse_obj(data, ('channel', {
            'url': ('playback_url', {url_or_none}, {require('Stream url')}),
            'token': ('playback_auth_token', {str}, {require('Stream token')}),
        }))

        formats = self._extract_m3u8_formats(
            stream_data['url'], creator_slug, live=True, query={
                'token': stream_data['token'],
                'player_version': '1.17.0',
            })

        return {
            'id': creator_slug,
            'formats': formats,
            'is_live': True,
            **traverse_obj(data, {
                'title': ('livestream_event_info', 'event_name', {str}),
                'description': ('livestream_event_info', 'event_description', {str}),
                'thumbnail': ('livestream_event_info', 'livestream_preview_file', {url_or_none}),
                'timestamp': ('stream', 'start_time', {parse_iso8601}),
                'view_count': ('stream', 'viewer_count', {int_or_none}),
            }),
        }
