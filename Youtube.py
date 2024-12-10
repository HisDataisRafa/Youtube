# youtube_extractor.py
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
from datetime import datetime
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import pandas as pd

class YouTubeExtractor:
    def __init__(self, api_key):
        """
        Initialize the YouTube extractor with your API key
        To get an API key, visit: https://console.cloud.google.com/
        """
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.output_dir = 'youtube_content'
        
        # Create directories if they don't exist
        for dir_name in ['thumbnails', 'transcripts', 'data']:
            dir_path = os.path.join(self.output_dir, dir_name)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

    def get_channel_videos(self, channel_id, max_results=50):
        """
        Get the most recent videos from a channel with their transcripts
        """
        try:
            # First get video IDs from the channel
            request = self.youtube.search().list(
                part="id",
                channelId=channel_id,
                maxResults=max_results,
                type="video",
                order="date"
            )
            
            response = request.execute()
            video_ids = [item['id']['videoId'] for item in response['items']]
            
            # Get full details for each video
            videos_data = []
            for video_id in video_ids:
                video_data = self._get_video_details(video_id)
                if video_data:
                    videos_data.append(video_data)
            
            # Save to JSON and CSV
            self._save_to_json(videos_data, f"channel_{channel_id}_content.json")
            self._save_to_csv(videos_data, f"channel_{channel_id}_content.csv")
            
            return videos_data
            
        except HttpError as e:
            print(f"An error occurred while fetching videos: {e}")
            return None

    def _get_video_details(self, video_id):
        """
        Get detailed information about a specific video, including its transcript
        """
        try:
            # Get video details from API
            request = self.youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                return None
                
            video = response['items'][0]
            video_data = {
                'video_id': video_id,
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'thumbnail_url': video['snippet']['thumbnails']['high']['url'],
                'published_at': video['snippet']['publishedAt'],
                'view_count': video['statistics'].get('viewCount', 0),
                'like_count': video['statistics'].get('likeCount', 0),
                'comment_count': video['statistics'].get('commentCount', 0)
            }
            
            # Download thumbnail
            thumbnail_path = self._download_thumbnail(
                video_data['thumbnail_url'],
                f"{video_id}.jpg"
            )
            video_data['thumbnail_local_path'] = thumbnail_path
            
            # Get and save transcript
            transcript = self._get_transcript(video_id)
            if transcript:
                video_data['transcript'] = transcript
                self._save_transcript(transcript, video_id)
            
            return video_data
            
        except Exception as e:
            print(f"Error getting video details for {video_id}: {e}")
            return None

    def _get_transcript(self, video_id):
        """
        Get the transcript of a video
        """
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            return transcript
        except Exception as e:
            print(f"Could not get transcript for video {video_id}: {e}")
            return None

    def _save_transcript(self, transcript, video_id):
        """
        Save the transcript to a text file
        """
        try:
            filepath = os.path.join(self.output_dir, 'transcripts', f"{video_id}.txt")
            with open(filepath, 'w', encoding='utf-8') as f:
                for entry in transcript:
                    f.write(f"{entry['text']}\n")
        except Exception as e:
            print(f"Error saving transcript: {e}")

    def _download_thumbnail(self, url, filename):
        """
        Download the video thumbnail
        """
        try:
            path = os.path.join(self.output_dir, 'thumbnails', filename)
            response = requests.get(url)
            response.raise_for_status()
            
            with open(path, 'wb') as f:
                f.write(response.content)
            
            return path
            
        except Exception as e:
            print(f"Error downloading thumbnail: {e}")
            return None

    def _save_to_json(self, data, filename):
        """
        Save the extracted data to a JSON file
        """
        try:
            path = os.path.join(self.output_dir, 'data', filename)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
        except Exception as e:
            print(f"Error saving JSON file: {e}")

    def _save_to_csv(self, data, filename):
        """
        Save the extracted data to a CSV file
        """
        try:
            path = os.path.join(self.output_dir, 'data', filename)
            df = pd.DataFrame(data)
            df.to_csv(path, index=False, encoding='utf-8')
                
        except Exception as e:
            print(f"Error saving CSV file: {e}")

# streamlit_app.py
import streamlit as st
import os
from youtube_extractor import YouTubeExtractor

def main():
    st.title("YouTube Content Extractor")
    st.write("Extract content from YouTube channels including thumbnails and transcripts")

    # API Key input
    api_key = st.text_input("Enter your YouTube API Key:", type="password")
    
    # Channel ID input
    channel_id = st.text_input("Enter YouTube Channel ID:")
    
    # Number of videos to extract
    max_results = st.slider("Number of videos to extract", 1, 50, 10)
    
    if st.button("Extract Content"):
        if not api_key or not channel_id:
            st.error("Please provide both API Key and Channel ID")
            return
            
        try:
            extractor = YouTubeExtractor(api_key)
            with st.spinner("Extracting content..."):
                videos = extractor.get_channel_videos(channel_id, max_results)
                
            if videos:
                st.success(f"Successfully extracted {len(videos)} videos!")
                
                # Display results
                for video in videos:
                    st.write("---")
                    st.write(f"**{video['title']}**")
                    if 'thumbnail_local_path' in video:
                        st.image(video['thumbnail_local_path'])
                    st.write(f"Views: {video['view_count']}")
                    st.write(f"Likes: {video['like_count']}")
                    if 'transcript' in video:
                        with st.expander("Show Transcript"):
                            transcript_text = "\n".join([entry['text'] for entry in video['transcript']])
                            st.text(transcript_text)
            else:
                st.error("No videos were extracted. Please check the channel ID and try again.")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()

# requirements.txt
google-api-python-client==2.88.0
requests==2.31.0
streamlit==1.22.0
youtube-transcript-api==0.6.0
pandas==2.0.2
