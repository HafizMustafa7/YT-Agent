
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import httpx
from supabase import create_client
from datetime import datetime, timezone


load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError('Please set SUPABASE_URL and SUPABASE_KEY in .env')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title='YT-Agent Analytics API')

YOUTUBE_DATA_API = 'https://www.googleapis.com/youtube/v3'
YOUTUBE_ANALYTICS_API = 'https://youtubeanalytics.googleapis.com/v2'
OAUTH2_TOKEN_URL = 'https://oauth2.googleapis.com/token'

class ChannelRow(BaseModel):
    id: str
    userid: str
    youtube_channelid: str
    yt_channel_name: Optional[str]
    access_token: Optional[str]
    refresh_token: Optional[str]
    token_expiry: Optional[datetime]
    created_at: Optional[datetime]


async def refresh_access_token(refresh_token: str) -> dict:
    """Use OAuth2 'refresh_token' to get new access token."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise RuntimeError('Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET')
    data = {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(OAUTH2_TOKEN_URL, data=data, timeout=30)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail='Failed to refresh token')
        return resp.json()


async def get_channel_row(channel_id: str) -> ChannelRow:
    resp = supabase.table('channels').select('*').eq('id', channel_id).single().execute()
    if resp.status_code != 200 and resp.data is None:
        raise HTTPException(status_code=404, detail='Channel not found')
    data = resp.data
    return ChannelRow(**data)


async def ensure_valid_token(channel: ChannelRow) -> str:
    """Return valid access token for the channel. Refresh if expired or near expiry."""
    now = datetime.now(timezone.utc)
    if channel.access_token and channel.token_expiry:
        if channel.token_expiry > now:
            return channel.access_token
    # otherwise, refresh
    if not channel.refresh_token:
        raise HTTPException(status_code=400, detail='No refresh token available')
    token_resp = await refresh_access_token(channel.refresh_token)
    new_access = token_resp.get('access_token')
    expires_in = token_resp.get('expires_in')
    if not new_access:
        raise HTTPException(status_code=502, detail='Failed to obtain new access token')
    expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in)) if expires_in else None
    # update supabase
    update = {
        'access_token': new_access,
        'token_expiry': expiry.isoformat() if expiry else None
    }
    supabase.table('channels').update(update).eq('id', channel.id).execute()
    return new_access


@app.get('/channels', response_model=List[ChannelRow])
async def list_channels():
    r = supabase.table('channels').select('*').execute()
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail='Error reading channels')
    return [ChannelRow(**row) for row in r.data]


@app.get('/channels/{channel_id}/videos')
async def list_videos(channel_id: str, max_results: int = 25):
    channel = await get_channel_row(channel_id)
    access_token = await ensure_valid_token(channel)
    # Get Uploads playlist id
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'part': 'contentDetails,snippet',
        'mine': 'true',
        'maxResults': max_results
    }
    # We'll attempt to list videos by searching for channel's uploaded videos using the search endpoint
    async with httpx.AsyncClient() as client:
        # Search for videos owned by the channel
        search_params = {'part': 'snippet', 'channelId': channel.youtube_channelid, 'order': 'date', 'maxResults': max_results, 'type': 'video'}
        resp = await client.get(f'{YOUTUBE_DATA_API}/search', params=search_params, headers=headers, timeout=30)
        resp.raise_for_status()
        items = resp.json().get('items', [])
        videos = []
        for it in items:
            vid = {
                'videoId': it['id']['videoId'],
                'title': it['snippet']['title'],
                'publishedAt': it['snippet']['publishedAt']
            }
            videos.append(vid)
    return {'videos': videos}


from datetime import timedelta

@app.get('/channels/{channel_id}/analytics')
async def channel_analytics(channel_id: str, metrics: str = 'views,likes,estimatedMinutesWatched', startDate: str = None, endDate: str = None):
    """Fetches basic channel analytics from YouTube Analytics API.

    metrics: comma-separated list of metrics, e.g. views,likes,estimatedMinutesWatched
    startDate/endDate are YYYY-MM-DD; defaults to last 30 days
    """
    channel = await get_channel_row(channel_id)
    access_token = await ensure_valid_token(channel)
    headers = {'Authorization': f'Bearer {access_token}'}
    # default dates
    from datetime import datetime, timedelta
    today = datetime.utcnow().date()
    if not endDate:
        endDate = today.isoformat()
    if not startDate:
        startDate = (today - timedelta(days=30)).isoformat()

    params = {
        'ids': f'channel=={channel.youtube_channelid}',
        'startDate': startDate,
        'endDate': endDate,
        'metrics': metrics,
        'dimensions': 'day',
        'sort': 'day'
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(f'{YOUTUBE_ANALYTICS_API}/reports', params=params, headers=headers, timeout=30)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
    return data


@app.get('/channels/{channel_id}/video_analytics/{video_id}')
async def video_analytics(channel_id: str, video_id: str, metrics: str = 'views,likes,estimatedMinutesWatched', startDate: str = None, endDate: str = None):
    channel = await get_channel_row(channel_id)
    access_token = await ensure_valid_token(channel)
    headers = {'Authorization': f'Bearer {access_token}'}
    from datetime import datetime, timedelta
    today = datetime.utcnow().date()
    if not endDate:
        endDate = today.isoformat()
    if not startDate:
        startDate = (today - timedelta(days=30)).isoformat()
    params = {
        'ids': f'channel=={channel.youtube_channelid}',
        'startDate': startDate,
        'endDate': endDate,
        'metrics': metrics,
        'filters': f'video=={video_id}',
        'dimensions': 'day',
        'sort': 'day'
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(f'{YOUTUBE_ANALYTICS_API}/reports', params=params, headers=headers, timeout=30)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
    return data


# Small health check
@app.get('/')
async def root():
    return {'status': 'ok'}