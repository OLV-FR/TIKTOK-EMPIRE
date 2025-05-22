import streamlit as st
import tempfile
from pathlib import Path
from joe_bot import process_video

# 🔧 Augmenter la taille max de téléversement à 1 Go
st.set_option('server.maxUploadSize', 1024)
st.set_page_config(page_title="TikBot Empire", page_icon="🎬")
st.title("🎬 TikBot Empire - Analyse intelligente de vidéos TikTok")


uploaded_video = st.file_uploader("Téléverse une vidéo au format MP4", type=["mp4"])

if uploaded_video:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
        tmp_file.write(uploaded_video.read())
        temp_video_path = tmp_file.name

    st.success("Vidéo téléversée avec succès !")

    if st.button("Lancer l'analyse"):
        with st.spinner("🔍 Analyse de la vidéo en cours..."):
            try:
                process_video(temp_video_path)
                st.success("✅ Analyse terminée !")

                output_dir = Path("Sortie")
                clips = list(output_dir.glob("*.mp4"))
                if clips:
                    st.subheader("📍 Extraits générés par TikBot Empire :")
                    for clip in clips:
                        st.video(str(clip))
                else:
                    st.warning("Aucun extrait vidéo détecté.")
            except Exception as e:
                st.error(f"❌ Une erreur est survenue : {e}")
