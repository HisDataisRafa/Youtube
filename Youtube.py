import streamlit as st
import requests
import json
from datetime import datetime

def get_channel_videos(api_key, channel_id, max_results=10):
    """
    Obtiene videos de un canal de YouTube usando solo requests
    """
    # Primero obtenemos el ID de los videos del canal
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
        response.raise_for_status()  # Verificar si hay errores
        search_data = response.json()
        
        # Extraer IDs de videos
        video_ids = [item['id']['videoId'] for item in search_data.get('items', [])]
        
        # Obtener detalles de los videos
        videos_url = "https://www.googleapis.com/youtube/v3/videos"
        videos_params = {
            "key": api_key,
            "id": ",".join(video_ids),
            "part": "snippet,statistics"
        }
        
        response = requests.get(videos_url, params=videos_params)
        response.raise_for_status()
        videos_data = response.json()
        
        # Procesar y retornar la información relevante
        videos = []
        for video in videos_data.get('items', []):
            videos.append({
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'thumbnail': video['snippet']['thumbnails']['high']['url'],
                'views': video['statistics'].get('viewCount', '0'),
                'likes': video['statistics'].get('likeCount', '0')
            })
        
        return videos
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error al obtener videos: {str(e)}")
        return None

def main():
    st.title("📺 YouTube Channel Explorer")
    st.write("Explora los videos más recientes de un canal de YouTube")
    
    # Configuración en la barra lateral
    st.sidebar.header("Configuración")
    api_key = st.sidebar.text_input("YouTube API Key", type="password")
    channel_id = st.sidebar.text_input("ID del Canal")
    max_results = st.sidebar.slider("Número de videos", 1, 50, 10)
    
    if st.button("Obtener Videos"):
        if not api_key or not channel_id:
            st.warning("Por favor ingresa la API key y el ID del canal.")
            return
            
        with st.spinner("Obteniendo videos..."):
            videos = get_channel_videos(api_key, channel_id, max_results)
            
        if videos:
            # Guardar datos para descarga
            df_data = []
            for video in videos:
                df_data.append({
                    'Título': video['title'],
                    'Vistas': video['views'],
                    'Likes': video['likes']
                })
                
            # Mostrar videos
            for video in videos:
                st.write("---")
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.image(video['thumbnail'])
                
                with col2:
                    st.write(f"### {video['title']}")
                    st.write(f"👁️ Vistas: {video['views']}  |  👍 Likes: {video['likes']}")
                    with st.expander("Ver descripción"):
                        st.write(video['description'])
            
            # Botón de descarga
            json_str = json.dumps(videos, ensure_ascii=False, indent=2)
            st.download_button(
                label="⬇️ Descargar datos (JSON)",
                data=json_str,
                file_name=f"youtube_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

if __name__ == "__main__":
    main()
