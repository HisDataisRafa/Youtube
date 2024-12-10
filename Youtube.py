import streamlit as st
import requests
import json
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import time

# Inicialización del estado de la sesión
if 'videos_data' not in st.session_state:
    st.session_state.videos_data = None

def get_transcript(video_id, target_language='es'):
    """
    Obtiene la transcripción de un video en el idioma especificado
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Definir idiomas preferidos según el idioma objetivo
        if target_language == 'es':
            preferred_languages = ['es', 'es-ES', 'es-419', 'es-US', 'en', 'en-US', 'en-GB']
        else:  # target_language == 'en'
            preferred_languages = ['en', 'en-US', 'en-GB', 'es', 'es-ES', 'es-419']
        
        transcript = None
        transcript_info = "No encontrada"
        original_language = None
        
        # Intentar obtener transcripción manual
        for lang in preferred_languages:
            try:
                available_manual = transcript_list.find_manually_created_transcript([lang])
                if available_manual:
                    transcript = available_manual
                    original_language = lang
                    transcript_info = f"Manual ({lang})"
                    break
            except:
                continue
        
        # Si no hay manual, intentar transcripción automática
        if not transcript:
            for lang in preferred_languages:
                try:
                    available_auto = transcript_list.find_generated_transcript([lang])
                    if available_auto:
                        transcript = available_auto
                        original_language = lang
                        transcript_info = f"Automática ({lang})"
                        break
                except:
                    continue
        
        # Si aún no hay transcripción, tomar cualquiera disponible
        if not transcript:
            try:
                available_transcripts = transcript_list.manual_transcripts
                if available_transcripts:
                    transcript = list(available_transcripts.values())[0]
                    original_language = transcript.language_code
                    transcript_info = f"Manual ({original_language})"
                else:
                    available_transcripts = transcript_list.generated_transcripts
                    if available_transcripts:
                        transcript = list(available_transcripts.values())[0]
                        original_language = transcript.language_code
                        transcript_info = f"Automática ({original_language})"
            except:
                pass
        
        # Si encontramos una transcripción, traducir si es necesario
        if transcript:
            try:
                # Verificar si necesitamos traducir
                should_translate = (target_language == 'es' and 
                                 original_language not in ['es', 'es-ES', 'es-419', 'es-US']) or \
                                (target_language == 'en' and 
                                 original_language not in ['en', 'en-US', 'en-GB'])
                
                if should_translate:
                    transcript = transcript.translate(target_language)
                    transcript_info += f" (Traducida a {target_language})"
            except Exception as e:
                st.warning(f"No se pudo traducir la transcripción: {str(e)}")
            
            transcript_data = transcript.fetch()
            return transcript_data, transcript_info, original_language
            
    except Exception as e:
        st.warning(f"No se pudo obtener la transcripción para el video {video_id}: {str(e)}")
    
    return None, "No disponible", None

# [El resto de las funciones (get_channel_id, get_channel_videos) permanecen igual]

def create_download_files(videos, target_language):
    """
    Crea los archivos de descarga en el idioma especificado
    """
    # Actualizar transcripciones al idioma seleccionado
    for video in videos:
        transcript_data, transcript_info, original_language = get_transcript(
            video['video_id'], 
            target_language
        )
        if transcript_data:
            video['transcript'] = "\n".join([f"{item['start']:.1f}s: {item['text']}" 
                                           for item in transcript_data])
            video['transcript_info'] = transcript_info
            video['original_language'] = original_language
    
    # Crear JSON
    json_str = json.dumps(videos, ensure_ascii=False, indent=2)
    
    # Crear TXT de transcripciones
    transcripts_text = ""
    for video in videos:
        if video['transcript']:
            transcripts_text += f"\n\n=== {video['title']} ===\n"
            transcripts_text += f"URL: {video['url']}\n"
            transcripts_text += f"Tipo: {video['transcript_info']}\n"
            transcripts_text += f"Idioma original: {video.get('original_language', 'Desconocido')}\n\n"
            transcripts_text += video['transcript']
            transcripts_text += "\n\n" + "="*50 + "\n"
    
    return json_str, transcripts_text

def main():
    st.set_page_config(page_title="YouTube Content Explorer", layout="wide")
    
    st.title("📺 YouTube Content Explorer")
    st.write("""
    Esta herramienta te permite explorar los videos más recientes de un canal de YouTube 
    y obtener sus transcripciones en español o inglés.
    """)
    
    # Configuración en la barra lateral
    st.sidebar.header("⚙️ Configuración")
    api_key = st.sidebar.text_input("YouTube API Key", type="password")
    channel_identifier = st.sidebar.text_input("ID/Nombre/Handle del Canal")
    max_results = st.sidebar.slider("Número de videos a obtener", 1, 50, 10)
    
    # Obtener videos
    if st.button("🔍 Obtener Videos y Transcripciones"):
        if not api_key or not channel_identifier:
            st.warning("⚠️ Por favor ingresa tanto la API key como el identificador del canal.")
            return
            
        with st.spinner("🔄 Obteniendo videos y transcripciones..."):
            videos = get_channel_videos(api_key, channel_identifier, max_results)
            if videos:
                st.session_state.videos_data = videos
    
    # Mostrar resultados si hay datos
    if st.session_state.videos_data:
        videos = st.session_state.videos_data
        st.success(f"✅ Se encontraron {len(videos)} videos!")
        
        # Sección de descarga con selección de idioma
        st.write("---")
        st.subheader("📥 Opciones de Descarga")
        
        col1, col2 = st.columns([2, 2])
        
        with col1:
            target_language = st.radio(
                "Selecciona el idioma para las transcripciones:",
                options=['es', 'en'],
                format_func=lambda x: "Español" if x == 'es' else "English"
            )
        
        with col2:
            if st.button("🔄 Preparar archivos para descarga"):
                with st.spinner("Preparando archivos..."):
                    json_str, transcripts_text = create_download_files(
                        videos.copy(), 
                        target_language
                    )
                    
                    lang_suffix = "es" if target_language == "es" else "en"
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        st.download_button(
                            label="⬇️ Descargar todo (JSON)",
                            data=json_str,
                            file_name=f"youtube_data_{lang_suffix}_{timestamp}.json",
                            mime="application/json"
                        )
                    
                    with col4:
                        st.download_button(
                            label="⬇️ Descargar transcripciones (TXT)",
                            data=transcripts_text,
                            file_name=f"transcripts_{lang_suffix}_{timestamp}.txt",
                            mime="text/plain"
                        )
        
        # Mostrar videos
        st.write("---")
        for video in videos:
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
                    col1, col2 = st.columns([3,1])
                    with col1:
                        if video['transcript']:
                            st.text_area("", value=video['transcript'], height=200)
                        else:
                            st.info("No hay transcripción disponible para este video")
                    with col2:
                        st.info(f"Tipo: {video['transcript_info']}")

if __name__ == "__main__":
    main()
