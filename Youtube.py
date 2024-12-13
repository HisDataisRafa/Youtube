import streamlit as st
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import time

# Configuración inicial de la página
st.set_page_config(page_title="YouTube Explorer", layout="wide")

def get_video_transcript(video_id):
    """
    Función simplificada para obtener transcripciones.
    Solo intenta obtener la transcripción una vez, sin traducciones.
    """
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join(item['text'] for item in transcript)
    except:
        return None

def get_videos(api_key, channel_id, max_results=5):
    """
    Función simplificada para obtener videos.
    Solo obtiene información básica y transcripción.
    """
    try:
        # Paso 1: Obtener IDs de los videos
        search_url = f"https://www.googleapis.com/youtube/v3/search"
        params = {
            "key": api_key,
            "channelId": channel_id,
            "part": "id",
            "order": "date",
            "maxResults": max_results,
            "type": "video"
        }
        
        with st.spinner("Buscando videos..."):
            response = requests.get(search_url, params=params)
            if not response.ok:
                st.error("Error al buscar videos")
                return None
                
            data = response.json()
            video_ids = [item['id']['videoId'] for item in data.get('items', [])]

        # Paso 2: Obtener detalles de los videos
        if video_ids:
            videos_url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                "key": api_key,
                "id": ",".join(video_ids),
                "part": "snippet,statistics"
            }
            
            with st.spinner("Obteniendo detalles..."):
                response = requests.get(videos_url, params=params)
                if not response.ok:
                    st.error("Error al obtener detalles")
                    return None
                    
                videos = []
                for video in response.json().get('items', []):
                    videos.append({
                        'title': video['snippet']['title'],
                        'thumbnail': video['snippet']['thumbnails']['high']['url'],
                        'video_id': video['id'],
                        'url': f"https://youtube.com/watch?v={video['id']}"
                    })
                    
                return videos
        return None
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def main():
    st.title("📺 YouTube Content Explorer")
    st.write("Versión simplificada para diagnóstico")
    
    # Entradas del usuario
    api_key = st.text_input("YouTube API Key", type="password")
    channel_id = st.text_input("ID del Canal")
    
    if st.button("Buscar"):
        if not api_key or not channel_id:
            st.warning("Por favor ingresa la API key y el ID del canal")
            return
            
        # Intentar obtener los videos
        videos = get_videos(api_key, channel_id, max_results=5)
        
        if videos:
            st.success(f"Se encontraron {len(videos)} videos")
            
            # Mostrar videos
            for video in videos:
                st.write("---")
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.image(video['thumbnail'])
                
                with col2:
                    st.markdown(f"### [{video['title']}]({video['url']})")
                    
                    # Obtener transcripción
                    with st.spinner(f"Obteniendo transcripción para {video['title']}..."):
                        transcript = get_video_transcript(video['video_id'])
                        if transcript:
                            st.text_area("Transcripción:", transcript, height=150)
                        else:
                            st.info("No hay transcripción disponible")

if __name__ == "__main__":
    main()
