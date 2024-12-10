import streamlit as st
import requests
import json
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import time
import zipfile
import io
import base64

# Configuración inicial
st.set_page_config(page_title="YouTube Explorer", layout="wide")

# Inicialización del estado
if 'videos_data' not in st.session_state:
    st.session_state.videos_data = None

def get_transcript(video_id, target_language='es'):
    """
    Obtiene la transcripción limpia, sin timestamps
    """
    try:
        start_time = time.time()
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        if time.time() - start_time > 5:
            return None, "Tiempo excedido", None

        try:
            if target_language == 'es':
                transcript = transcript_list.find_transcript(['es'])
            else:
                transcript = transcript_list.find_transcript(['en'])
        except NoTranscriptFound:
            try:
                if target_language == 'es':
                    transcript = transcript_list.find_transcript(['en']).translate('es')
                else:
                    transcript = transcript_list.find_transcript(['es']).translate('en')
            except:
                return None, "No disponible", None

        # Obtenemos solo el texto, sin timestamps
        transcript_data = transcript.fetch()
        clean_transcript = ' '.join(item['text'] for item in transcript_data)
        return clean_transcript, f"Transcripción en {target_language.upper()}", transcript.language_code

    except Exception as e:
        return None, str(e), None

def download_thumbnails(videos):
    """
    Crea un archivo ZIP con todas las miniaturas
    """
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

def get_channel_videos(api_key, channel_identifier, max_results=10):
    """
    Obtiene los videos del canal (resto de la función igual, solo cambia cómo guardamos la transcripción)
    """
    try:
        status_text = st.empty()
        progress_bar = st.progress(0)
        status_text.text("Buscando canal...")

        # [... resto del código igual hasta el procesamiento de videos ...]

        # En el procesamiento de videos, modificamos cómo guardamos la transcripción:
        for i, video in enumerate(videos_data):
            current_progress = 0.4 + (0.6 * (i + 1) / total_videos)
            status_text.text(f"Procesando video {i+1} de {total_videos}...")
            progress_bar.progress(current_progress)

            video_info = {
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'thumbnail': video['snippet']['thumbnails']['high']['url'],
                'views': video['statistics'].get('viewCount', '0'),
                'likes': video['statistics'].get('likeCount', '0'),
                'url': f"https://youtube.com/watch?v={video['id']}",
                'video_id': video['id']
            }

            transcript_text, transcript_info, original_language = get_transcript(video['id'])
            if transcript_text:
                video_info['transcript'] = transcript_text
                video_info['transcript_info'] = transcript_info
                video_info['original_language'] = original_language
            else:
                video_info['transcript'] = ""
                video_info['transcript_info'] = transcript_info
                video_info['original_language'] = None

            videos.append(video_info)
            time.sleep(0.1)

        status_text.empty()
        progress_bar.empty()
        return videos

    except Exception as e:
        st.error(f"Error inesperado: {str(e)}")
        return None

def main():
    st.title("📺 YouTube Content Explorer")
    st.write("Explora videos y transcripciones de canales de YouTube")

    with st.sidebar:
        api_key = st.text_input("YouTube API Key", type="password")
        channel_identifier = st.text_input("ID o Nombre del Canal")
        max_results = st.slider("Número de videos", 1, 20, 5)

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
        
        # Sección de descargas
        st.subheader("📥 Opciones de descarga")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            language = st.radio(
                "Idioma de transcripción:",
                ['es', 'en'],
                format_func=lambda x: "Español" if x == 'es' else "English",
                horizontal=True
            )

        with col2:
            # Botón para descargar transcripciones
            transcripts = []
            for video in st.session_state.videos_data:
                if video.get('transcript'):
                    transcripts.append(f"=== {video['title']} ===\n{video['url']}\n\n{video['transcript']}\n")
            
            if transcripts:
                st.download_button(
                    "📝 Descargar transcripciones (TXT)",
                    "\n\n".join(transcripts),
                    f"transcripts_{language}_{datetime.now():%Y%m%d_%H%M}.txt",
                    "text/plain"
                )

        with col3:
            # Botón para descargar miniaturas
            if st.button("🖼️ Descargar miniaturas (ZIP)"):
                with st.spinner("Preparando miniaturas..."):
                    zip_data = download_thumbnails(st.session_state.videos_data)
                    b64_zip = base64.b64encode(zip_data).decode()
                    href = f'data:application/zip;base64,{b64_zip}'
                    st.markdown(
                        f'<a href="{href}" download="thumbnails_{datetime.now():%Y%m%d_%H%M}.zip">📥 Clic aquí para descargar las miniaturas</a>',
                        unsafe_allow_html=True
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
                    else:
                        st.info("No hay transcripción disponible")

if __name__ == "__main__":
    main()
