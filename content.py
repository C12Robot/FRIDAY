import os
import re
import requests
from datetime import datetime, timedelta
from anthropic import Anthropic
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

client       = Anthropic()
YT_API_KEY   = os.getenv("YOUTUBE_API_KEY")
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
YT_CREDS_FILE  = os.path.join(BASE_DIR, "youtube_credentials.json")
YT_TOKEN_FILE_MAIN  = os.path.join(BASE_DIR, "youtube_token_main.json")
YT_TOKEN_FILE_SECOND  = os.path.join(BASE_DIR, "youtube_token_second.json")
ANALYTICS_SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]

CHANNEL_IDS = {
    "main":    "UCjmUItlB6yax4G7SFIixOgQ",
    "second":  "UCTZ14IF5fTzQxndSGy35u6A"
}



def get_analytics_service():
    creds = None
    if os.path.exists(YT_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(YT_TOKEN_FILE, ANALYTICS_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(YT_CREDS_FILE, ANALYTICS_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(YT_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("youtubeAnalytics", "v2", credentials=creds)


def get_data_service():
    return build("youtube", "v3", developerKey=YT_API_KEY)



def search_trending(niche="futures trading finance"):
    try:
        yt = get_data_service()
        response = yt.search().list(
            part="snippet",
            q=niche,
            type="video",
            order="viewCount",
            publishedAfter=(datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            maxResults=10
        ).execute()

        videos = []
        for item in response.get("items", []):
            title     = item["snippet"]["title"]
            channel   = item["snippet"]["channelTitle"]
            video_id  = item["id"]["videoId"]
            videos.append(f"- {title} ({channel}) https://youtube.com/watch?v={video_id}")

        if not videos:
            return "No trending videos found."

        trending_list = "\n".join(videos)

        response2 = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            system="You are a YouTube content strategist. Identify 3 content opportunities from these trending videos for a formula 1 technical and funny commentary channel. Be specific and actionable.",
            messages=[{"role": "user", "content": f"Trending videos this week:\n{trending_list}"}]
        )
        return response2.content[0].text.strip()
    except Exception as e:
        return f"Trend search error: {str(e)}"


def get_video_comments(video_url, max_comments=30):
    try:
        video_id_match = re.search(r"(?:v=|youtu\.be/)([^&\n]+)", video_url)
        if not video_id_match:
            return "Invalid YouTube URL."
        video_id = video_id_match.group(1)

        yt = get_data_service()
        response = yt.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_comments,
            order="relevance"
        ).execute()

        comments = []
        for item in response.get("items", []):
            text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(text[:200])

        if not comments:
            return "No comments found."

        comments_text = "\n".join(comments)
        response2 = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            system="Summarise YouTube comments into content insights. What do viewers want more of? What questions keep coming up? What pain points appear? Be specific.",
            messages=[{"role": "user", "content": f"Comments:\n{comments_text}"}]
        )
        return response2.content[0].text.strip()
    except Exception as e:
        return f"Comment fetch error: {str(e)}"



def get_channel_stats(channel="main"):
    try:
        service    = get_analytics_service(channel)
        end_date   = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")
        channel_id = CHANNEL_IDS.get(channel, "")

        response = service.reports().query(
            ids=f"channel=={channel_id}",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched,likes",
            dimensions="day",
            sort="day"
        ).execute()

        rows = response.get("rows", [])
        if not rows:
            return "No analytics data found."

        total_views     = sum(r[1] for r in rows)
        total_watchtime = sum(r[2] for r in rows)
        total_likes     = sum(r[3] for r in rows)

        return (
            f"Last 28 days — {channel} channel:\n"
            f"Views: {int(total_views):,}\n"
            f"Watch time: {int(total_watchtime/60):,} hours\n"
            f"Likes: {int(total_likes):,}"
        )
    except Exception as e:
        return f"Analytics error: {str(e)}"


def get_best_upload_time(channel="main"):
    try:
        service    = get_analytics_service(channel)
        end_date   = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        channel_id = CHANNEL_IDS.get(channel, "")
        if not channel_id:
            return f"Channel ID for '{channel}' not set."

        response = service.reports().query(
            ids=f"channel=={channel_id}",
            startDate=start_date,
            endDate=end_date,
            metrics="views",
            dimensions="day"
        ).execute()

        rows = response.get("rows", [])
        if not rows:
            return "Not enough data yet."

        data_text = "\n".join([f"{r[0]}: {r[1]} views" for r in rows[-30:]])

        response2 = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=150,
            system="Analyse this YouTube view data by day and suggest the best days and approximate times to upload. Be specific.",
            messages=[{"role": "user", "content": data_text}]
        )
        return response2.content[0].text.strip()
    except Exception as e:
        return f"Upload time error: {str(e)}"


def get_top_videos(channel="main"):
    try:
        service    = get_analytics_service()
        end_date   = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        channel_id = CHANNEL_IDS.get(channel, "")
        if not channel_id:
            return f"Channel ID for '{channel}' not set."

        response = service.reports().query(
            ids=f"channel=={channel_id}",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched,likes",
            dimensions="video",
            sort="-views",
            maxResults=5
        ).execute()

        rows = response.get("rows", [])
        if not rows:
            return "No video data found."


        yt       = get_data_service()
        video_ids = ",".join([r[0] for r in rows])
        titles_response = yt.videos().list(
            part="snippet",
            id=video_ids
        ).execute()

        titles = {item["id"]: item["snippet"]["title"] for item in titles_response.get("items", [])}

        lines = ["Top 5 videos (last 90 days):"]
        for i, r in enumerate(rows, 1):
            title = titles.get(r[0], r[0])
            lines.append(f"{i}. {title} — {int(r[1]):,} views, {int(r[2]/60):,} hrs watch time")
        return "\n".join(lines)
    except Exception as e:
        return f"Top videos error: {str(e)}"



def generate_video_ideas(niche="F1 Formula 1 funny commentary news"):
    try:
        trending = search_trending(niche)
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=300,
            system="""You are a YouTube strategist for two channels:
            1. MAIN CHANNEL (F1/Formula 1): 80% funny high quality commentary, 20% technical. Focus on F1 news, documentaries, race commentary. Titles should be punchy, entertaining, slightly dramatic.
            2. SECOND CHANNEL (World of Warships): 100% funny gameplay commentary with light technical tips. Titles should be playful and gamer-focused.
            Generate 5 video ideas with title and one-line hook each. Ask which channel if not specified.""",
            messages=[{"role": "user", "content": f"Trending context:\n{trending}\n\nGenerate 5 video ideas for a formula 1 channel."}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Idea generation error: {str(e)}"


def generate_script_outline(topic):
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=400,
            system="""You write YouTube script outlines. 
            For F1/Formula 1 content: 80% entertaining commentary, 20% technical. Punchy, fast-paced, dramatic. Think Sky Sports F1 but funnier.
            For World of Warships content: funny gameplay commentary, light on technical, heavy on personality and reactions.
            Structure: Hook (30 sec), Intro, 3-4 sections, CTA. Be specific to the topic.""",
            messages=[{"role": "user", "content": f"Write a script outline for: {topic}"}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Script error: {str(e)}"


def suggest_content_from_stats(channel="main"):
    try:
        stats     = get_channel_stats(channel)
        top_vids  = get_top_videos(channel)
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=250,
            system="""You are a YouTube growth strategist for two channels:
            - Main (F1): funny commentary, news, documentaries. 80% entertainment 20% technical.
            - Second (WoW gameplay): funny commentary, light technical.
            Based on stats and top videos, suggest 3 specific content directions. Be actionable and channel-specific.""",
            messages=[{"role": "user", "content": f"Channel stats:\n{stats}\n\nTop videos:\n{top_vids}"}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Content suggestion error: {str(e)}"

def get_analytics_service(channel="main"):
    token_file = YT_TOKEN_FILE_MAIN if channel == "main" else YT_TOKEN_FILE_SECOND
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, ANALYTICS_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(YT_CREDS_FILE, ANALYTICS_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    return build("youtubeAnalytics", "v2", credentials=creds)