import streamlit as st
import requests
import json
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import time

# Configuración inicial para mostrar mejor el progreso
st.set_page_config(page_title="YouTube Explorer", layout="wide")

# Inicialización del estado
if 'videos_data' not in st.session_state:
    st.session_state.videos_data = None
if 'processing_status' not in st.session_state:
    st.session_state.processing_status = None

def get_transcript(video_id, target_language='es'):
    """
    Obtiene la transcripción intentando múltiples métodos y fuentes
    """
    try:
        # Lista de idiomas a intentar para español
        spanish_langs = ['es', 'es-ES', 'es-419', 'es-MX', 'es-AR', 'es-US']
        # Lista de idiomas a intentar para inglés
        english_langs = ['en', 'en-US', 'en-GB', 'en-CA', 'en-IN']
        
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = None
        
        # Paso 1: Intentar obtener transcripción manual en el idioma objetivo
        try:
            if target_language == 'es':
                for lang in spanish_langs:
                    try:
                        transcript = transcript_list.find_manually_created_transcript([lang])
                        break
                    except:
                        continue
            else:
                for lang in english_langs:
                    try:
                        transcript = transcript_list.find_manually_created_transcript([lang])
                        break
                    except:
                        continue
        except:
            pass

        # Paso 2: Si no hay manual, intentar transcripción automática en el idioma objetivo
        if not transcript:
            try:
                if target_language == 'es':
                    for lang in spanish_langs:
                        try:
                            transcript = transcript_list.find_generated_transcript([lang])
                            break
                        except:
                            continue
                else:
                    for lang in english_langs:
                        try:
                            transcript = transcript_list.find_generated_transcript([lang])
                            break
                        except:
                            continue
            except:
                pass

        # Paso 3: Intentar obtener cualquier transcripción manual y traducir
        if not transcript:
            try:
                available_transcripts = transcript_list.manual_transcripts
                if available_transcripts:
                    first_transcript = list(available_transcripts.values())[0]
                    transcript = first_transcript.translate(target_language)
            except:
                pass

        # Paso 4: Como último recurso, intentar cualquier transcripción automática y traducir
        if not transcript:
            try:
                available_transcripts = transcript_list.generated_transcripts
                if available_transcripts:
                    first_transcript = list(available_transcripts.values())[0]
                    transcript = first_transcript.translate(target_language)
            except:
                pass

        # Si encontramos alguna transcripción, procesarla
        if transcript:
            transcript_data = transcript.fetch()
            clean_text = ' '.join(item['text'] for item in transcript_data)
            transcript_info = f"Transcripción en {target_language.upper()}"
            if transcript.is_generated:
                transcript_info += " (Automática)"
            if transcript.language_code != target_language:
                transcript_info += f" (Traducida de {transcript.language_code})"
            return clean_text, transcript_info, transcript.language_code

        return None, "No se encontró transcripción", None

    except Exception as e:
        return None, str(e), None

def get_channel_videos(api_key, channel_identifier, max_results=10):
    """
    Versión optimizada de la obtención de videos
    """
    try:
        # Mostrar estado inicial
        status_text = st.empty()
        progress_bar = st.progress(0)
        status_text.text("Buscando canal...")

        # Obtener ID del canal
        search_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "key": api_key,
            "q": channel_identifier,
            "type": "channel",
            "part": "id",
            "maxResults": 1
        }
        
        response = requests.get(search_url, params=params)
        if not response.ok:
            st.error("Error al buscar el canal. Verifica el identificador.")
            return None

        data = response.json()
        if not data.get('items'):
            st.error("No se encontró el canal.")
            return None

        channel_id = data['items'][0]['id']['channelId']
        status_text.text("Obteniendo lista de videos...")
        progress_bar.progress(0.2)

        # Obtener videos del canal
        videos_params = {
            "key": api_key,
            "channelId": channel_id,
            "part": "id",
            "order": "date",
            "maxResults": max_results,
            "type": "video"
        }

        response = requests.get(search_url, params=videos_params)
        if not response.ok:
            st.error("Error al obtener videos del canal.")
            return None

        video_ids = [item['id']['videoId'] for item in response.json().get('items', [])]
        if not video_ids:
            st.warning("No se encontraron videos en este canal.")
            return None

        # Obtener detalles de los videos
        status_text.text("Obteniendo detalles de los videos...")
        progress_bar.progress(0.4)

        videos_url = "https://www.googleapis.com/youtube/v3/videos"
        details_params = {
            "key": api_key,
            "id": ",".join(video_ids),
            "part": "snippet,statistics"
        }

        response = requests.get(videos_url, params=details_params)
        if not response.ok:
            st.error("Error al obtener detalles de los videos.")
            return None

        videos_data = response.json().get('items', [])
        videos = []
        total_videos = len(videos_data)

        for i, video in enumerate(videos_data):
            current_progress = 0.4 + (0.6 * (i + 1) / total_videos)
            status_text.text(f"Procesando video {i+1} de {total_videos}...")
            progress_bar.progress(current_progress)

            # Procesar video actual
            video_info = {
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'thumbnail': video['snippet']['thumbnails']['high']['url'],
                'views': video['statistics'].get('viewCount', '0'),
                'likes': video['statistics'].get('likeCount', '0'),
                'url': f"https://youtube.com/watch?v={video['id']}",
                'video_id': video['id']
            }

            # Obtener transcripción con tiempo límite
            transcript_data, transcript_info, original_language = get_transcript(video['id'])
            if transcript_data:
                video_info['transcript'] = transcript_data  # Ahora transcript_data ya es texto limpio
                video_info['transcript_info'] = transcript_info
                video_info['original_language'] = original_language
            else:
                video_info['transcript'] = ""
                video_info['transcript_info'] = transcript_info
                video_info['original_language'] = None

            videos.append(video_info)
            time.sleep(0.1)  # Pequeña pausa para no sobrecargar la API

        status_text.empty()
        progress_bar.empty()
        return videos

    except Exception as e:
        st.error(f"Error inesperado: {str(e)}")
        return None

def download_thumbnails(videos):
    """
    Crea un archivo ZIP con todas las miniaturas
    """
    import io
    import zipfile
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, video in enumerate(videos, 1):
            try:
                # Descarga la miniatura
                response = requests.get(video['thumbnail'])
                if response.ok:
                    # Usa el título del video (limpiado) como nombre de archivo
                    safe_title = "".join(c for c in video['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
                    filename = f"{i:02d}-{safe_title[:50]}.jpg"
                    zip_file.writestr(filename, response.content)
            except Exception as e:
                st.warning(f"No se pudo descargar la miniatura de: {video['title']}")
                continue

    return zip_buffer.getvalue()

def main():
    st.title("📺 YouTube Content Explorer")
    st.write("Explora videos y transcripciones de canales de YouTube")

    with st.sidebar:
        api_key = st.text_input("YouTube API Key", type="password")
        channel_identifier = st.text_input("ID o Nombre del Canal")
        max_results = st.slider("Número de videos", 1, 20, 5)  # Reducido a 20 para mejor rendimiento

    if st.button("🔍 Buscar Videos"):
        if not api_key or not channel_identifier:
            st.warning("Por favor ingresa la API key y el identificador del canal.")
            return

        videos = get_channel_videos(api_key, channel_identifier, max_results)
        if videos:
            st.session_state.videos_data = videos
            st.success(f"Se encontraron {len(videos)} videos!")

    if st.session_state.videos_data:
        st.write("---")
        language = st.radio(
            "Idioma de transcripción:",
            ['es', 'en'],
            format_func=lambda x: "Español" if x == 'es' else "English",
            horizontal=True
        )

        # Botones de descarga
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # JSON con todo
            json_str = json.dumps(st.session_state.videos_data, ensure_ascii=False, indent=2)
            st.download_button(
                "⬇️ Descargar datos (JSON)",
                json_str,
                f"youtube_data_{language}_{datetime.now():%Y%m%d_%H%M}.json",
                "application/json"
            )
        
        with col2:
            # TXT solo transcripciones
            transcripts = []
            for video in st.session_state.videos_data:
                if video.get('transcript'):
                    transcripts.append(f"=== {video['title']} ===\n{video['url']}\n\n{video['transcript']}\n")
            
            if transcripts:
                st.download_button(
                    "⬇️ Descargar transcripciones (TXT)",
                    "\n\n".join(transcripts),
                    f"transcripts_{language}_{datetime.now():%Y%m%d_%H%M}.txt",
                    "text/plain"
                )
        
        with col3:
            # Botón para descargar miniaturas
            if st.button("🖼️ Descargar miniaturas"):
                with st.spinner("Preparando miniaturas..."):
                    zip_data = download_thumbnails(st.session_state.videos_data)
                    st.download_button(
                        "⬇️ Descargar miniaturas (ZIP)",
                        zip_data,
                        f"thumbnails_{datetime.now():%Y%m%d_%H%M}.zip",
                        "application/zip"
                    )

        # Mostrar videos
        for video in st.session_state.videos_data:
            st.write("---")
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.image(video['thumbnail'])
            
            with col2:
                st.markdown(f"### [{video['title']}]({video['url']})")
                st.write(f"👁️ Vistas: {int(video['views']):,}  |  👍 Likes: {int(video['likes']):,}")
                
                tab1, tab2 = st.tabs(["📝 Descripción", "🎯 Transcripción"])
                with tab1:
                    st.write(video['description'])
                with tab2:
                    if video.get('transcript'):
                        st.text_area("", video['transcript'], height=200)
                        st.info(video['transcript_info'])
                    else:
                        st.info("No hay transcripción disponible")

if __name__ == "__main__":
    main()
