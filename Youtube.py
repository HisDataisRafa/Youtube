import streamlit as st
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import pandas as pd
import requests
import os
import json

class YouTubeExtractor:
    def __init__(self, api_key):
        """
        Esta clase maneja toda la lógica de extracción de YouTube.
        Inicializa la conexión con la API de YouTube usando tu clave API.
        """
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Creamos directorios temporales para almacenar contenido
        self.temp_dir = 'temp_content'
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def get_channel_videos(self, channel_id, max_results=10):
        """
        Obtiene los videos más recientes de un canal y sus transcripciones
        """
        try:
            # Buscamos los videos del canal
            request = self.youtube.search().list(
                part="id",
                channelId=channel_id,
                maxResults=max_results,
                type="video",
                order="date"
            )
            
            response = request.execute()
            videos_data = []
            
            # Procesamos cada video encontrado
            for item in response['items']:
                video_id = item['id']['videoId']
                video_data = self._get_video_details(video_id)
                if video_data:
                    videos_data.append(video_data)
            
            return videos_data
            
        except Exception as e:
            st.error(f"Error al obtener videos: {str(e)}")
            return None

    def _get_video_details(self, video_id):
        """
        Obtiene los detalles completos de un video específico
        """
        try:
            request = self.youtube.videos().list(
                part="snippet,statistics",
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                return None
                
            video = response['items'][0]
            
            # Intentamos obtener la transcripción
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                transcript_text = "\n".join([entry['text'] for entry in transcript])
            except:
                transcript_text = "Transcripción no disponible"
            
            return {
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'thumbnail_url': video['snippet']['thumbnails']['high']['url'],
                'views': video['statistics'].get('viewCount', '0'),
                'likes': video['statistics'].get('likeCount', '0'),
                'transcript': transcript_text
            }
            
        except Exception as e:
            st.error(f"Error al obtener detalles del video: {str(e)}")
            return None

def main():
    st.set_page_config(page_title="YouTube Content Extractor", layout="wide")
    
    st.title("📺 YouTube Content Extractor")
    st.write("Herramienta para extraer contenido de canales de YouTube incluyendo transcripciones")
    
    # Input para la API Key
    api_key = st.text_input("Ingresa tu API Key de YouTube:", type="password")
    
    # Input para el ID del canal
    channel_id = st.text_input("Ingresa el ID del canal de YouTube:")
    
    # Selector para número de videos
    max_videos = st.slider("Número de videos a extraer", 1, 50, 10)
    
    if st.button("Extraer Contenido"):
        if not api_key or not channel_id:
            st.error("Por favor proporciona tanto la API Key como el ID del canal")
            return
            
        try:
            with st.spinner("Extrayendo contenido..."):
                extractor = YouTubeExtractor(api_key)
                videos = extractor.get_channel_videos(channel_id, max_videos)
                
            if videos:
                st.success(f"¡Se extrajeron {len(videos)} videos exitosamente!")
                
                # Crear un DataFrame para descargar
                df = pd.DataFrame(videos)
                
                # Botón para descargar como CSV
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Descargar datos como CSV",
                    data=csv,
                    file_name="youtube_data.csv",
                    mime="text/csv"
                )
                
                # Mostrar los videos
                for video in videos:
                    st.write("---")
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.image(video['thumbnail_url'])
                    
                    with col2:
                        st.write(f"### {video['title']}")
                        st.write(f"👁️ Views: {video['views']}  |  👍 Likes: {video['likes']}")
                        with st.expander("Ver descripción"):
                            st.write(video['description'])
                        with st.expander("Ver transcripción"):
                            st.write(video['transcript'])
        
        except Exception as e:
            st.error(f"Ocurrió un error: {str(e)}")

if __name__ == "__main__":
    main()
