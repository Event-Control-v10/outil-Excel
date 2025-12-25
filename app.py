import streamlit as st
import pandas as pd
from groq import Groq
from streamlit_audiorecorder import audiorecorder
import io
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Excel AI Magic", page_icon="✨", layout="centered")

# --- DESIGN & CSS (La partie "Jolie") ---
st.markdown("""
<style>
    /* 1. FOND DE PAGE (Dégradé moderne) */
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

    /* 2. CARTES (Effet Verre / Glassmorphism) */
    div.css-1r6slb0, div.stVerticalBlock, .stDataFrame {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        margin-bottom: 20px;
    }
    
    /* Titres */
    h1 {
        color: white !important;
        text-shadow: 2px 2px 4px #000000;
        text-align: center;
        font-weight: 800;
        padding-bottom: 20px;
    }
    h3 {
        color: #333;
        font-weight: 600;
    }

    /* 3. BOUTONS STYLISÉS */
    .stButton>button {
        background-image: linear-gradient(to right, #1FA2FF 0%, #12D8FA  51%, #1FA2FF  100%);
        margin: 10px;
        padding: 15px 45px;
        text-align: center;
        text-transform: uppercase;
        transition: 0.5s;
        background-size: 200% auto;
        color: white;            
        box-shadow: 0 0 20px #eee;
        border-radius: 50px;
        border: none;
        display: block;
        width: 100%;
        font-weight: bold;
    }

    .stButton>button:hover {
        background-position: right center; /* change the direction of the change here */
        color: #fff;
        text-decoration: none;
    }
    
    /* Zone de texte */
    .stTextInput > div > div > input {
        border-radius: 15px;
        padding: 10px;
        border: 2px solid #ddd;
    }

    /* Uploader */
    .stFileUploader {
        padding: 20px;
        border: 2px dashed #1FA2FF;
        border-radius: 20px;
        text-align: center;
        background-color: rgba(255,255,255,0.8);
    }
    
    /* Masquer le menu Streamlit par défaut */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- LOGIQUE (Backend) ---

try:
    api_key = st.secrets["GROQ_API_KEY"]
except:
    # Pour le dev local si besoin
    api_key = st.text_input("Clé API Groq (Mode Test)", type="password")

if not api_key:
    st.info("👋 Bienvenue ! Veuillez configurer la clé API dans les secrets pour démarrer.")
    st.stop()

client = Groq(api_key=api_key)

def transcribe_audio(audio_bytes):
    try:
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", audio_bytes), 
            model="whisper-large-v3",
            language="fr"
        )
        return transcription.text
    except Exception as e:
        return None

def get_python_code(df_head, instruction):
    prompt = f"""
    Tu es un data scientist Python expert. 
    DataFrame 'df' :
    {df_head}
    
    Instruction : "{instruction}"
    
    Écris le code Python pour modifier 'df'. 
    Règles :
    1. Modifie 'df' directement.
    2. QUE le code, pas de markdown (```), pas d'explication.
    3. Importe pandas as pd et numpy as np.
    """
    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    code = completion.choices[0].message.content
    return code.replace("```python", "").replace("```", "").strip()

# --- INTERFACE VISUELLE ---

st.title("✨ Assistant Excel IA")
st.markdown("<p style='text-align: center; color: white; margin-bottom: 30px;'>Donnez vie à vos données par la voix ou le texte.</p>", unsafe_allow_html=True)

# Conteneur 1 : Upload
with st.container():
    st.write("### 📂 Étape 1 : Votre Fichier")
    uploaded_file = st.file_uploader("Glissez votre fichier Excel ici", type=['xlsx'], label_visibility="collapsed")

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    
    # Affichage stylisé des données
    with st.expander("👁️ Voir l'aperçu des données", expanded=True):
        st.dataframe(df.head(), use_container_width=True)

    # Conteneur 2 : Instruction
    with st.container():
        st.write("### 🗣️ Étape 2 : Votre Instruction")
        
        # Onglets pour nettoyer l'interface
        tab1, tab2 = st.tabs(["🎙️ Vocal", "⌨️ Texte"])
        
        instruction = ""
        
        with tab1:
            st.write("Cliquez sur le micro, parlez, puis cliquez sur stop.")
            audio = audiorecorder("🔴 Enregistrer", "⬛ Stop")
            if len(audio) > 0:
                st.success("Audio capturé !")
                transcribed = transcribe_audio(audio.tobytes())
                if transcribed:
                    st.info(f"J'ai compris : \"{transcribed}\"")
                    instruction = transcribed
        
        with tab2:
            text_input = st.text_area("Décrivez la modification souhaitée", height=100)
            if text_input:
                instruction = text_input

    # Conteneur 3 : Action et Résultat
    if instruction:
        st.write("---")
        if st.button("✨ Lancer la Magie"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("🧠 L'IA analyse votre demande...")
            progress_bar.progress(30)
            
            try:
                # 1. Code generation
                code = get_python_code(df.head().to_string(), instruction)
                progress_bar.progress(60)
                status_text.text("⚙️ Application des modifications...")
                
                # 2. Execution
                local_vars = {'df': df, 'pd': pd}
                exec(code, {}, local_vars)
                df_new = local_vars['df']
                
                progress_bar.progress(100)
                status_text.text("✅ Terminé !")
                time.sleep(0.5)
                status_text.empty()
                progress_bar.empty()
                
                st.balloons() # Petite animation festive
                
                st.success("Modifications appliquées avec succès !")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("#### Résultat :")
                    st.dataframe(df_new.head(), use_container_width=True)
                
                with col2:
                    st.write("#### Télécharger :")
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
                st.error("Oups, l'IA a trébuché sur le code. Essayez de reformuler l'instruction.")
                st.error(e)

else:
    # Message d'accueil quand rien n'est chargé
    st.info("👆 Commencez par uploader un fichier Excel ci-dessus.")