import streamlit as st
import pandas as pd
from groq import Groq
from audiorecorder import audiorecorder
import io
import time
import numpy as np

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Excel AI Magic", page_icon="✨", layout="centered")

# --- DESIGN & CSS ---
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
    }
    @keyframes gradient {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }
    div.stVerticalBlock, .stDataFrame {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        backdrop-filter: blur(4px);
        margin-bottom: 20px;
    }
    h1 { color: white !important; text-align: center; font-weight: 800; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
    .stButton>button {
        background-image: linear-gradient(to right, #1FA2FF 0%, #12D8FA  51%, #1FA2FF  100%);
        border-radius: 50px; color: white; border: none; width: 100%; font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.02); }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- LOGIQUE ---

try:
    api_key = st.secrets["GROQ_API_KEY"]
except:
    api_key = st.sidebar.text_input("Clé API Groq", type="password")

if not api_key:
    st.info("👋 Veuillez configurer la clé API dans les secrets Streamlit (Paramètres -> Secrets).")
    st.stop()

client = Groq(api_key=api_key)

def transcribe_audio(audio_bytes):
    try:
        # On utilise le modèle whisper stable
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", audio_bytes), 
            model="whisper-large-v3",
            language="fr"
        )
        return transcription.text
    except Exception as e:
        st.error(f"Erreur de transcription : {e}")
        return None

def get_python_code(df_head, instruction):
    # Mise à jour vers le nouveau modèle llama-3.3-70b-versatile
    prompt = f"""
    Tu es un data scientist expert. Voici le head d'un DataFrame nommé 'df' :
    {df_head}
    
    Instruction de l'utilisateur : {instruction}
    
    Écris UNIQUEMENT le code Python pur pour modifier ce DataFrame 'df'. 
    Règles :
    - Pas de texte explicatif.
    - Pas de balises markdown (comme ```python).
    - Ne pas recharger le fichier.
    - Utilise pandas (déjà importé sous 'pd') et numpy (déjà importé sous 'np').
    """
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    code = completion.choices[0].message.content
    return code.replace("```python", "").replace("```", "").strip()

# --- INTERFACE ---

st.title("✨ Assistant Excel IA")

with st.container():
    st.write("### 📂 Étape 1 : Votre Fichier")
    uploaded_file = st.file_uploader("Upload", type=['xlsx', 'xls'], label_visibility="collapsed")

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    with st.expander("👁️ Aperçu des données originales"):
        st.dataframe(df.head(), use_container_width=True)

    with st.container():
        st.write("### 🗣️ Étape 2 : Votre Instruction")
        tab1, tab2 = st.tabs(["🎙️ Vocal", "⌨️ Texte"])
        instruction = ""
        
        with tab1:
            st.write("Le micro nécessite que FFmpeg soit installé sur le serveur.")
            audio = audiorecorder("🔴 Enregistrer", "⬛ Stop")
            if len(audio) > 0:
                with st.spinner("L'IA écoute votre voix..."):
                    transcribed = transcribe_audio(audio.tobytes())
                    if transcribed:
                        st.success(f"Compris : \"{transcribed}\"")
                        instruction = transcribed
        
        with tab2:
            text_input = st.text_area("Exemple: 'Ajoute 20% à la colonne prix' ou 'Supprime les lignes vides'...")
            if text_input: instruction = text_input

    if instruction:
        if st.button("✨ Lancer la Magie"):
            try:
                # 1. Génération du code
                with st.spinner("Génération du code..."):
                    code = get_python_code(df.head().to_string(), instruction)
                
                # 2. Exécution du code
                # On prépare l'environnement pour exec()
                local_vars = {'df': df, 'pd': pd, 'np': np}
                exec(code, {}, local_vars)
                df_new = local_vars['df']
                
                st.balloons()
                st.success("Modifications terminées !")
                
                # Affichage du résultat
                st.write("#### Résultat :")
                st.dataframe(df_new.head(), use_container_width=True)
                
                # Préparation du téléchargement
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_new.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 Télécharger le fichier modifié",
                    data=buffer.getvalue(),
                    file_name="resultat_ia.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Désolé, l'IA a rencontré une erreur technique : {e}")
else:
    st.info("👆 Commencez par glisser-déposer un fichier Excel pour activer l'IA.")
