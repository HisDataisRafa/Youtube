def get_channel_videos(api_key, channel_identifier, max_results=10):
    """
    Obtiene los videos más recientes de un canal junto con sus detalles y transcripciones
    """
    # Obtener el ID correcto del canal
    channel_id = get_channel_id(api_key, channel_identifier)
    if not channel_id:
        return None
        
    # Obtener los IDs de los videos más recientes
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
        
        # Obtener detalles completos de los videos
        videos_url = "https://www.googleapis.com/youtube/v3/videos"
        videos_params = {
            "key": api_key,
            "id": ",".join(video_ids),
            "part": "snippet,statistics"
        }
        
        response = requests.get(videos_url, params=videos_params)
        response.raise_for_status()
        videos_data = response.json()
        
        # Procesar cada video
        videos = []
        progress_text = st.empty()
        progress_bar = st.progress(0)
        total_videos = len(videos_data.get('items', []))
        
        for i, video in enumerate(videos_data.get('items', [])):
            progress_text.text(f"Procesando video {i+1} de {total_videos}...")
            progress_bar.progress((i + 1) / total_videos)
            
            # Obtener transcripción en español por defecto
            transcript_data, transcript_info, original_language = get_transcript(video['id'], 'es')
            transcript_text = ""
            if transcript_data:
                transcript_text = "\n".join([f"{item['start']:.1f}s: {item['text']}" for item in transcript_data])
            
            # Recopilar toda la información del video
            videos.append({
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'thumbnail': video['snippet']['thumbnails']['high']['url'],
                'views': video['statistics'].get('viewCount', '0'),
                'likes': video['statistics'].get('likeCount', '0'),
                'url': f"https://youtube.com/watch?v={video['id']}",
                'transcript': transcript_text,
                'transcript_info': transcript_info,
                'original_language': original_language,
                'video_id': video['id']
            })
            
            # Pequeña pausa para evitar límites de API
            time.sleep(0.5)
        
        progress_text.empty()
        progress_bar.empty()
        return videos
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error al obtener videos: {str(e)}")
        return None
