def get_channel_videos(api_key, channel_identifier, max_results=10):
    """
    Obtiene los videos del canal y sus detalles incluyendo transcripciones.
    La función maneja todo el proceso de manera ordenada:
    1. Busca el canal
    2. Obtiene la lista de videos
    3. Obtiene los detalles de cada video
    4. Procesa las transcripciones
    """
    try:
        # Inicializamos elementos visuales para mostrar el progreso
        status_text = st.empty()
        progress_bar = st.progress(0)
        status_text.text("Buscando canal...")

        # Paso 1: Obtener ID del canal
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

        # Paso 2: Obtener lista de videos del canal
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

        # Paso 3: Obtener detalles completos de cada video
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

        # Aquí es donde estaba el error - Ahora definimos videos_data correctamente
        videos_data = response.json().get('items', [])
        
        # Paso 4: Procesar cada video y obtener transcripciones
        videos = []  # Lista para almacenar todos los videos procesados
        total_videos = len(videos_data)

        for i, video in enumerate(videos_data):
            current_progress = 0.4 + (0.6 * (i + 1) / total_videos)
            status_text.text(f"Procesando video {i+1} de {total_videos}...")
            progress_bar.progress(current_progress)

            # Recopilamos la información básica del video
            video_info = {
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'thumbnail': video['snippet']['thumbnails']['high']['url'],
                'views': video['statistics'].get('viewCount', '0'),
                'likes': video['statistics'].get('likeCount', '0'),
                'url': f"https://youtube.com/watch?v={video['id']}",
                'video_id': video['id']
            }

            # Obtenemos y procesamos la transcripción
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
            time.sleep(0.1)  # Pequeña pausa para no sobrecargar la API

        # Limpiamos los elementos visuales de progreso
        status_text.empty()
        progress_bar.empty()
        
        return videos

    except Exception as e:
        st.error(f"Error inesperado: {str(e)}")
        return None
