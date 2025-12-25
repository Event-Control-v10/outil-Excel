import streamlit as st
import pandas as pd
from groq import Groq
from audiorecorder import audiorecorder
import io
import time
import numpy as np

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Excel AI Surgical", page_icon="🎯", layout="centered")

# --- DESIGN & CSS ---
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(-45deg, #1e3c72, #2a5298, #2c3e50);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
    }
    @keyframes gradient {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }
    div.stVerticalBlock, .stDataFrame {
        background-color: rgba(255, 255, 255, 0.98);
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        margin-bottom: 20px;
    }
    h1 { color: white !important; text-align: center; font-family: 'Segoe UI', sans-serif; }
    .stButton>button {
        background: #00c6ff;
        background: -webkit-linear-gradient(to right, #0072ff, #00c6ff);
        background: linear-gradient(to right, #0072ff, #00c6ff);
        border-radius: 10px; color: white; border: none; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIQUE ---

try:
    api_key = st.secrets["GROQ_API_KEY"]
except:
    api_key = st.sidebar.text_input("Clé API Groq", type="password")

if not api_key:
    st.info("👋 Veuillez configurer la clé API Groq.")
    st.stop()

client = Groq(api_key=api_key)

def transcribe_audio(audio_file_obj):
    try:
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", audio_file_obj), 
            model="whisper-large-v3",
            language="fr"
        )
        return transcription.text
    except Exception as e:
        return None

def get_python_code(df_head, instruction):
    # PROMPT CHIRURGICAL : On force l'IA à être très spécifique
    prompt = f"""
    Tu es un expert en manipulation de données Python Pandas.
    Voici un aperçu du fichier (DataFrame 'df') :
    {df_head}

    CONSIGNE UTILISATEUR : "{instruction}"

    RÈGLES STRICTES :
    1. Sois CHIRURGICAL. Ne modifie QUE les données demandées. 
    2. N'écrase pas toute une colonne si l'utilisateur demande de changer une seule ligne.
    3. Utilise 'df.at[index, "colonne"]' ou 'df.loc' pour des changements précis.
    4. Ne change JAMAIS les noms des colonnes existantes sauf si demandé.
    5. Ne crée pas de nouvelles colonnes sauf si demandé.
    6. Renvoie UNIQUEMENT le code Python, sans commentaires, sans balises markdown.
    """
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": "Tu es un assistant qui génère du code Python Pandas précis."},
                  {"role": "user", "content": prompt}],
        temperature=0
    )
    code = completion.choices[0].message.content
    return code.replace("```python", "").replace("```", "").strip()

# --- INTERFACE ---

st.title("🎯 Assistant Excel Précis")

uploaded_file = st.file_uploader("Avec ta grosse tête faut deposer ton fichier là", type=['xlsx'], label_visibility="collapsed")

if uploaded_file:
    # On garde une copie du fichier original en mémoire
    df = pd.read_excel(uploaded_file)
    
    st.write("### 👁️ Données actuelles")
    st.dataframe(df.head(10), use_container_width=True)

    st.write("---")
    st.write("### 🛠️ Quelle modification faire ?")
    
    tab1, tab2 = st.tabs(["🎙️ Vocal", "⌨️ Texte"])
    instruction = ""
    
    with tab1:
        audio = audiorecorder("🔴 Enregistrer", "⬛ Stop")
        if len(audio) > 0:
            audio_bio = io.BytesIO()
            audio.export(audio_bio, format="wav")
            audio_bio.seek(0)
            with st.spinner("L'IA écoute..."):
                transcribed = transcribe_audio(audio_bio)
                if transcribed:
                    st.success(f"Entendu : \"{transcribed}\"")
                    instruction = transcribed
    
    with tab2:
        text_input = st.text_input("Ex: 'Change le nom de la ligne 2 par Pierre' ou 'Mets 0 dans la case A5'")
        if text_input: instruction = text_input

    if instruction:
        if st.button("🚀 Appliquer le changement ciblé"):
            try:
                # On travaille sur une copie pour pouvoir comparer
                df_modified = df.copy()
                
                with st.spinner("Réflexion chirurgicale..."):
                    code = get_python_code(df.head(20).to_string(), instruction)
                
                # Exécution
                local_vars = {'df': df_modified, 'pd': pd, 'np': np}
                exec(code, {}, local_vars)
                df_final = local_vars['df']
                
                st.balloons()
                st.success("Modification effectuée !")
                
                st.write("### ✅ Résultat (uniquement les lignes touchées)")
                # On montre les lignes qui ont changé (ou les premières lignes)
                st.dataframe(df_final.head(10), use_container_width=True)
                
                # Téléchargement
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_final.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 Télécharger le fichier corrigé",
                    data=output.getvalue(),
                    file_name="excel_modifie.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Erreur technique : {e}")
                st.info("Conseil : Essayez d'être plus précis (ex: précisez le nom de la colonne).")
