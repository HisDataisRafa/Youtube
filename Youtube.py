import streamlit as st
import requests
import json
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

def get_channel_id(api_key, channel_identifier):
    """
    Obtiene el ID del canal a partir de un nombre de usuario o handle.
    """
    if channel_identifier.startswith('UC'):
        return channel_identifier
        
    if channel_identifier.startswith('@'):
        channel_identifier = channel_identifier[1:]
    
    search_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": api_key,
        "q": channel_identifier,
        "type": "channel",
        "part": "id",
        "maxResults": 1
    }
    
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if 'items' in data and data['items']:
            return data['items'][0]['id']['channelId']
        else:
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error al buscar el canal: {str(e)}")
        return None

def get_transcript(video_id):
    """
    Obtiene la transcripción de un video
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Intentar obtener transcripción en español primero
        try:
            transcript = transcript_list.find_transcript(['es'])
        except NoTranscriptFound:
            # Si no hay en español, obtener en cualquier idioma y traducir
            transcript = transcript_list.find_transcript(['en'])
            transcript = transcript.translate('es')
            
        return transcript.fetch()
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception as e:
        print(f"Error obteniendo transcripción para {video_id}: {str(e)}")
        return None

def get_channel_videos(api_key, channel_identifier, max_results=10):
    """
    Obtiene videos de un canal de YouTube con sus transcripciones
    """
    channel_id = get_channel_id(api_key, channel_identifier)
    if not channel_id:
        st.error("No se pudo encontrar el canal. Verifica el identificador.")
        return None
        
    search_url = "https://www.googleapis.com/youtube/v3/search"
    search_params = {
        "key": api_key,
        "channelId": channel_id,
        "part": "id",
        "order": "date",
        "maxResults": max_results,
        "type": "video"
    }
    
    try:
        response = requests.get(search_url, params=search_params)
        response.raise_for_status()
        search_data = response.json()
        
        video_ids = [item['id']['videoId'] for item in search_data.get('items', [])]
        
        if not video_ids:
            st.warning("No se encontraron videos en este canal.")
            return None
        
        videos_url = "https://www.googleapis.com/youtube/v3/videos"
        videos_params = {
            "key": api_key,
            "id": ",".join(video_ids),
            "part": "snippet,statistics"
        }
        
        response = requests.get(videos_url, params=videos_params)
        response.raise_for_status()
        videos_data = response.json()
        
        videos = []
        progress_text = st.empty()
        progress_bar = st.progress(0)
        total_videos = len(videos_data.get('items', []))
        
        for i, video in enumerate(videos_data.get('items', [])):
            progress_text.text(f"Procesando video {i+1} de {total_videos}...")
            progress_bar.progress((i + 1) / total_videos)
            
            # Obtener transcripción
            transcript = get_transcript(video['id'])
            transcript_text = ""
            if transcript:
                transcript_text = "\n".join([f"{item['start']:.1f}s: {item['text']}" for item in transcript])
            
            videos.append({
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'thumbnail': video['snippet']['thumbnails']['high']['url'],
                'views': video['statistics'].get('viewCount', '0'),
                'likes': video['statistics'].get('likeCount', '0'),
                'url': f"https://youtube.com/watch?v={video['id']}",
                'transcript': transcript_text
            })
        
        progress_text.empty()
        progress_bar.empty()
        return videos
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error al obtener videos: {str(e)}")
        return None

def main():
    st.title("📺 YouTube Channel Explorer")
    st.write("""
    Explora los videos más recientes de un canal de YouTube.
    Puedes usar:
    - ID del canal (comienza con UC...)
    - Nombre de usuario
    - Handle (comienza con @)
    """)
    
    st.sidebar.header("Configuración")
    api_key = st.sidebar.text_input("YouTube API Key", type="password")
    channel_identifier = st.sidebar.text_input("ID/Nombre/Handle del Canal")
    max_results = st.sidebar.slider("Número de videos", 1, 50, 10)
    
    if st.button("Obtener Videos"):
        if not api_key or not channel_identifier:
            st.warning("Por favor ingresa la API key y el identificador del canal.")
            return
            
        with st.spinner("Obteniendo videos y transcripciones..."):
            videos = get_channel_videos(api_key, channel_identifier, max_results)
            
        if videos:
            # Mostrar videos
            for video in videos:
                st.write("---")
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.image(video['thumbnail'])
                
                with col2:
                    st.markdown(f"### [{video['title']}]({video['url']})")
                    st.write(f"👁️ Vistas: {video['views']}  |  👍 Likes: {video['likes']}")
                    
                    # Pestañas para descripción y transcripción
                    tab1, tab2 = st.tabs(["📝 Descripción", "🎯 Transcripción"])
                    with tab1:
                        st.write(video['description'])
                    with tab2:
                        if video['transcript']:
                            st.text_area("", value=video['transcript'], height=200)
                        else:
                            st.info("No hay transcripción disponible para este video")
            
            # Botones de descarga
            col1, col2 = st.columns(2)
            with col1:
                json_str = json.dumps(videos, ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️ Descargar todo (JSON)",
                    data=json_str,
                    file_name=f"youtube_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            with col2:
                # Crear archivo de texto solo con transcripciones
                transcripts_text = ""
                for video in videos:
                    if video['transcript']:
                        transcripts_text += f"\n\n=== {video['title']} ===\n{video['url']}\n\n"
                        transcripts_text += video['transcript']
                        transcripts_text += "\n\n" + "="*50 + "\n"
                
                st.download_button(
                    label="⬇️ Descargar solo transcripciones (TXT)",
                    data=transcripts_text,
                    file_name=f"transcripts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )

if __name__ == "__main__":
    main()
