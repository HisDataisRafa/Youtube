import streamlit as st
import requests
import json
from datetime import datetime

def get_channel_id(api_key, channel_identifier):
    """
    Obtiene el ID del canal a partir de un nombre de usuario o handle.
    Retorna el ID directamente si ya es un ID válido.
    """
    # Si ya es un ID de canal (comienza con UC), lo retornamos directamente
    if channel_identifier.startswith('UC'):
        return channel_identifier
        
    # Si es un handle (@), removemos el @ para la búsqueda
    if channel_identifier.startswith('@'):
        channel_identifier = channel_identifier[1:]
    
    # Intentamos buscar el canal
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

def get_channel_videos(api_key, channel_identifier, max_results=10):
    """
    Obtiene videos de un canal de YouTube usando el identificador proporcionado
    """
    # Primero obtenemos el ID correcto del canal
    channel_id = get_channel_id(api_key, channel_identifier)
    if not channel_id:
        st.error("No se pudo encontrar el canal. Verifica el identificador.")
        return None
        
    # Luego obtenemos los videos
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
        
        videos = []
        for video in videos_data.get('items', []):
            videos.append({
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'thumbnail': video['snippet']['thumbnails']['high']['url'],
                'views': video['statistics'].get('viewCount', '0'),
                'likes': video['statistics'].get('likeCount', '0'),
                'url': f"https://youtube.com/watch?v={video['id']}"
            })
        
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
    
    # Configuración en la barra lateral
    st.sidebar.header("Configuración")
    api_key = st.sidebar.text_input("YouTube API Key", type="password")
    channel_identifier = st.sidebar.text_input("ID/Nombre/Handle del Canal")
    max_results = st.sidebar.slider("Número de videos", 1, 50, 10)
    
    if st.button("Obtener Videos"):
        if not api_key or not channel_identifier:
            st.warning("Por favor ingresa la API key y el identificador del canal.")
            return
            
        with st.spinner("Obteniendo videos..."):
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
