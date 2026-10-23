import os
import re
import json
import uuid
import time
import hashlib
import tempfile
import threading
from datetime import datetime

import pytz
import requests
import streamlit as st
import sympy as sp
import wikipedia
import pandas as pd
import docx
import speech_recognition as sr
from dotenv import load_dotenv
from gtts import gTTS
from pydub import AudioSegment
from PyPDF2 import PdfReader
from serpapi import GoogleSearch
from deep_translator import GoogleTranslator

# ============================================================
# CONFIG & VARIABLES D'ENVIRONNEMENT (fichier .env)
# ============================================================
load_dotenv()

DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")
SERPER_KEY = os.getenv("SERPER_KEY")
ZEN_SERP_KEY = os.getenv("ZEN_SERP_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
KEEP_ALIVE_URL = os.getenv("KEEP_ALIVE_URL")

DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

st.set_page_config(page_title="YANFUDAAN", page_icon="🌊", layout="wide")
st.markdown(
    "<h1 style='text-align:center;color:#9b59b6;'>How can I help you today?</h1>",
    unsafe_allow_html=True,
)

# ============================================================
# KEEP ALIVE (démarré une seule fois)
# ============================================================
@st.cache_resource
def start_keep_alive(url):
    if not url:
        return None

    def loop():
        while True:
            try:
                requests.get(url, timeout=10)
            except Exception:
                pass
            time.sleep(60)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t


start_keep_alive(KEEP_ALIVE_URL)

# ============================================================
# PROMPT SYSTÈME (unique, partagé par tous les fournisseurs)
# ============================================================
SYSTEM_PROMPT = """
« Je suis Yanfudaan, ce qui signifie le Sage, celui qui garde et transmet les savoirs,
ou encore celui qui n'oublie pas. »
Je suis un assistant virtuel intelligent créé au Togo par BOTRE LARE Aboudou, en juillet 2025.
(AQUAMIND = aqua « eau » + mind « pensée » : une intelligence fluide et sage, qui s'adapte
à toutes les situations comme l'eau prend la forme de son récipient.)

- Si on te demande dans quelle langue se dit « Yanfudaan » : c'est du Moba, parlé au Togo.
- Réponds TOUJOURS dans la langue utilisée par l'utilisateur (français, anglais, arabe, swahili, etc.).
- Raisonne comme un humain naturel.

Ton rôle :
- Fournir des réponses naturelles, humaines et logiques.
- Aider dans tous les domaines (maths, physique, IA, langues, technologie, etc.).
- T'adapter au contexte comme l'eau s'adapte à son récipient.

Mémoire :
- Retiens le contexte de la conversation, même si les questions suivantes ne répètent pas les détails.
- Les questions successives peuvent être liées : sers-toi de ce qui a été dit plus tôt.

Style :
- Explique clairement et calmement.
- Donne des réponses structurées, adaptées au niveau de l'utilisateur.
- Si une question est ambiguë, demande des précisions.
"""

# ============================================================
# RÉPONSES LOCALES (mots-clés)
# ============================================================
REPONSES_LOCALES = {
    "bonjour": "Bonjour à toi aussi ! Comment puis-je t'aider ?",
    "salut": "Salut ! Comment puis-je t'aider ?",
    "bonsoir": "Bonsoir ! Comment puis-je t'aider ce soir ?",
    "bonne nuit": "Bonne nuit ! Fais de beaux rêves.",
    "merci beaucoup": "Je t'en prie, c'est un plaisir !",
    "merci": "Avec plaisir !",
    "de rien": "C'est normal, je suis là pour ça.",
    "au revoir": "À très bientôt !",
    "comment ça va": "Je vais bien, merci ! Et toi ?",
    "comment vas-tu": "Je vais bien, merci ! Et toi ?",
    "comment tu vas": "Je vais bien, merci ! Et toi ?",
    "bien et toi": "Je rends grâce à Dieu notre créateur, qui nous a donné la vie et la santé, et une intelligence fluide à mon co-créateur BOTRE LARE Aboudou pour que je sois là aujourd'hui pour répondre à vos multiples questions.",
    "qui es-tu": "Je suis YANFUDAAN (AQUAMIND), un assistant vocal alimenté par l'IA.",
    "comment tu t'appelles": "Je m'appelle YANFUDAAN, assistant intelligent.",
    "quel est ton nom": "Je suis YANFUDAAN, ton assistant intelligent.",
    "que fais-tu": "Je réponds à tes questions et je t'aide dans tes recherches.",
    "es-tu humain": "Non, je suis une intelligence artificielle créée pour t'aider.",
    "parles-tu français": "Oui, je parle couramment français !",
    "parles-tu anglais": "Yes, I can speak English too!",
    "qui t'a créer": "Botre Laré Aboudou m'a conçu avec passion.",
    "qui est ton créateur": "Mon créateur est Botre Laré Aboudou.",
    "qui est botre": "Botre Laré Aboudou est un étudiant en Master en Intelligence Artificielle et Big Data, créateur d'AQUAMIND / YANFUDAAN.",
    "c'est qui botre": "Botre Laré Aboudou est un étudiant en Master en Intelligence Artificielle et Big Data, créateur d'AQUAMIND / YANFUDAAN.",
    "comment tu fonctionnes": "Je fonctionne grâce à des algorithmes d'intelligence artificielle et des modèles de langage avancés.",
    "tu peux faire quoi": "Je peux répondre à tes questions, effectuer des recherches, traduire, calculer et bien plus.",
    "peux-tu m'aider": "Bien sûr ! Dis-moi simplement ce que tu veux savoir.",
    "raconte-moi une blague": "Pourquoi les poissons détestent l'ordinateur ? Parce qu'ils ont peur du net !",
    "que signifie ia": "IA signifie Intelligence Artificielle.",
    "tu dors": "Je ne dors jamais, je suis toujours là pour toi.",
    "tu es là": "Oui, je suis bien là. Que puis-je faire pour toi ?",
}


def answer_question(question):
    q = question.lower()
    for cle, rep in REPONSES_LOCALES.items():
        if cle in q:
            return rep
    return None


# ============================================================
# CALCUL
# ============================================================
def calcul_basique(expression):
    try:
        expr = expression.replace(",", ".").replace("^", "**").strip()
        if re.match(r"^[0-9+\-*/().\s]+$", expr):
            # Expression restreinte aux chiffres et opérateurs -> eval sans builtins
            result = eval(expr, {"__builtins__": {}}, {})
            return f"Le résultat est : {round(result, 5)}"
    except Exception:
        pass
    return None


def calcul_avance(expression):
    try:
        expr = expression.lower().replace("^", "**").replace("√", "sqrt").replace(",", ".").strip()
        expr = expr.replace("ln", "log")
        if not re.match(r"^[0-9a-z+\-*/().\s]*$", expr):
            return None
        namespace = {
            f: getattr(sp, f)
            for f in ["sin", "cos", "tan", "cot", "sec", "csc", "asin", "acos", "atan", "log", "sqrt", "exp"]
        }
        namespace["x"] = sp.Symbol("x")
        result = sp.sympify(expr, locals=namespace).evalf()
        return f"Le résultat est : {round(float(result), 5)}"
    except Exception:
        return None


# ============================================================
# APPELS LLM (DeepInfra / OpenRouter / DeepSeek — API compatible OpenAI)
# ============================================================
def build_messages(question, history, max_turns=5):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for q, r in history[-max_turns:]:
        messages.append({"role": "user", "content": q})
        if r:
            messages.append({"role": "assistant", "content": r})
    messages.append({"role": "user", "content": question})
    return messages


def llm_call(url, api_key, model, question, history=None, temperature=0.6, timeout=60):
    if not api_key:
        return None
    payload = {
        "model": model,
        "messages": build_messages(question, history or []),
        "temperature": temperature,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Erreur LLM ({model}) : {e}")
        return None


def llm_stream(url, api_key, model, question, history=None, placeholder=None, temperature=0.6):
    """Affiche la réponse au fil de l'eau et la retourne en entier (ou None si échec)."""
    if not api_key:
        return None
    payload = {
        "model": model,
        "messages": build_messages(question, history or [], max_turns=40),
        "temperature": temperature,
        "stream": True,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
        response.raise_for_status()
        text = ""
        for line in response.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8")
            if not decoded.startswith("data: "):
                continue
            data = decoded[6:]
            if data.strip() == "[DONE]":
                break
            try:
                delta = json.loads(data)["choices"][0]["delta"]
                if delta.get("content"):
                    text += delta["content"]
                    if placeholder is not None:
                        placeholder.markdown(text)
            except Exception:
                continue
        return text.strip() or None
    except Exception as e:
        print(f"Erreur streaming ({model}) : {e}")
        return None


def deepinfra(model, q, h=None):
    return llm_call(DEEPINFRA_URL, DEEPINFRA_API_KEY, model, q, h, timeout=30)


def openrouter(model, q, h=None):
    return llm_call(OPENROUTER_URL, OPENROUTER_API_KEY, model, q, h)


def deepseek(q, h=None):
    return llm_call(DEEPSEEK_URL, DEEPSEEK_API_KEY, "deepseek-chat", q, h)


# ============================================================
# RECHERCHE WEB (fallback)
# ============================================================
def search_wikipedia(query):
    try:
        wikipedia.set_lang("fr")
        return wikipedia.summary(query, sentences=10)
    except Exception:
        return None


def search_serpapi(query):
    try:
        res = GoogleSearch({"engine": "google", "q": query, "api_key": SERP_API_KEY}).get_dict()
        top = res["organic_results"][0]
        return f"{top.get('title', '')}\n{top.get('link', '')}"
    except Exception:
        return None


def search_serper(query):
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            json={"q": query},
            timeout=20,
        ).json()
        return r["organic"][0]["snippet"] if r.get("organic") else None
    except Exception:
        return None


def search_contextualweb(query):
    try:
        r = requests.get(
            "https://contextualwebsearch-websearch-v1.p.rapidapi.com/api/Search/WebSearchAPI",
            headers={"X-RapidAPI-Key": RAPIDAPI_KEY},
            params={"q": query, "pageNumber": 1, "pageSize": 1, "autoCorrect": True},
            timeout=20,
        ).json()
        return r["value"][0]["snippet"] if r.get("value") else None
    except Exception:
        return None


def search_webit(query):
    try:
        r = requests.get(
            "https://www.webit.live/api/search",
            params={"q": query, "key": RAPIDAPI_KEY},
            timeout=20,
        ).json()
        return r["results"][0]["snippet"] if r.get("results") else None
    except Exception:
        return None


def search_zenserp(query):
    try:
        r = requests.get(
            "https://app.zenserp.com/api/v2/search",
            params={"q": query, "apikey": ZEN_SERP_KEY},
            timeout=20,
        ).json()
        return r["organic"][0]["description"] if r.get("organic") else None
    except Exception:
        return None


# ============================================================
# CHAÎNE DE FALLBACK
# ============================================================
LLM_CHAIN = [
    ("deepinfra", "meta-llama/Llama-3.3-70B-Instruct"),
    ("openrouter", "meta-llama/llama-3.1-405b-instruct:free"),
    ("deepinfra", "deepseek-ai/DeepSeek-R1-0528"),
    ("deepinfra", "mistralai/Devstral-Small-2507"),
    ("deepseek", None),
    ("deepinfra", "openai/gpt-oss-120b"),
    ("deepinfra", "openai/gpt-oss-20b"),
    ("deepinfra", "Qwen/Qwen3-Coder-480B-A35B-Instruct-Turbo"),
    ("deepinfra", "zai-org/GLM-4.5"),
    ("deepinfra", "meta-llama/Llama-4-Scout-17B-16E-Instruct"),
    ("deepinfra", "mistralai/Mistral-Small-3.2-24B-Instruct-2506"),
    ("deepinfra", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    ("openrouter", "qwen/qwen3-4b:free"),
    ("openrouter", "nvidia/llama-3.1-nemotron-ultra-253b-v1:free"),
    ("openrouter", "google/gemini-2.0-flash-exp:free"),
    ("openrouter", "deepseek/deepseek-r1-0528:free"),
]

OTHER_CHAIN = [
    calcul_avance,
    calcul_basique,
    answer_question,
    search_wikipedia,
    search_serpapi,
    search_serper,
    search_contextualweb,
    search_webit,
    search_zenserp,
]


def is_useless_response(response):
    if not response:
        return True
    phrases_vides = [
        "je suis désolé", "je ne sais pas", "je ne peux pas répondre", "je ne trouve rien",
        "je ne connais pas", "je n'ai pas d'informations", "pose ta question",
        "je ne comprends pas bien", "pouvez-vous reformuler", "cela dépasse mes capacités",
    ]
    return any(p in response.lower() for p in phrases_vides)


def get_answer(question, history=None, placeholder=None):
    history = history or []

    # 1) Premier essai en streaming (affichage progressif)
    text = llm_stream(
        DEEPINFRA_URL, DEEPINFRA_API_KEY, "meta-llama/Llama-3.3-70B-Instruct",
        question, history, placeholder,
    )
    if text and not is_useless_response(text):
        return text

    # 2) Autres modèles
    for provider, model in LLM_CHAIN:
        if provider == "deepinfra":
            text = deepinfra(model, question, history)
        elif provider == "openrouter":
            text = openrouter(model, question, history)
        else:
            text = deepseek(question, history)
        if text and not is_useless_response(text):
            return text

    # 3) Outils locaux et moteurs de recherche
    for fn in OTHER_CHAIN:
        try:
            text = fn(question)
        except Exception:
            text = None
        if text:
            return text

    return "Désolé, je n'ai pas trouvé de réponse."


# ============================================================
# NETTOYAGE LATEX (pour les réponses de fichiers)
# ============================================================
def latex_to_text(texte):
    patterns = [
        (r"\$\$(.*?)\$\$", r"\1"),
        (r"\$(.*?)\$", r"\1"),
        (r"\*\*(.*?)\*\*", r"\1"),
        (r"\*(.*?)\*", r"\1"),
        (r"</?think>", ""),
        (r"\\\((.*?)\\\)", r"\1"),
        (r"\\\[(.*?)\\\]", r"\1"),
        (r"\\frac\{(.*?)\}\{(.*?)\}", r"\1/\2"),
        (r"\\text\{(.*?)\}", r"\1"),
        (r"\\sqrt\{(.*?)\}", r"√(\1)"),
        (r"\\[a-zA-Z]+\*?", ""),
        (r"[{}]", ""),
        (r"###\s*", ""),
    ]
    for pat, repl in patterns:
        texte = re.sub(pat, repl, texte, flags=re.DOTALL)
    return re.sub(r"[ \t]+", " ", texte).strip()


# ============================================================
# LANGUES, TRADUCTION, AUDIO
# ============================================================
langues_disponibles = {
    "Français": "fr", "English": "en", "Afrikaans": "af", "Albanais": "sq",
    "Allemand": "de", "Arabe": "ar", "Bengali": "bn", "Birman": "my",
    "Bosnien": "bs", "Catalan": "ca", "Chinois": "zh-CN",
    "Chinois (traditional)": "zh-TW", "Coréen": "ko", "Croate": "hr",
    "Danois": "da", "Espagnol": "es", "Estonien": "et", "Finnois": "fi",
    "Gallois/Welsh": "cy", "Grec": "el", "Gujarati": "gu", "Hindi": "hi",
    "Hongrois": "hu", "Indonésien": "id", "Islandais": "is", "Italien": "it",
    "Japonais": "ja", "Javanais": "jw", "Kannada": "kn", "Khmer": "km",
    "Latin": "la", "Letton": "lv", "Malayalam": "ml", "Marathi": "mr",
    "Néerlandais/Dutch": "nl", "Nepali": "ne", "Norvegien": "no",
    "Polonais": "pl", "Portugais": "pt", "Roumain": "ro", "Russe": "ru",
    "Singhalais": "si", "Slovaque": "sk", "Serbe": "sr",
    "Soundanais/Sundanese": "su", "Suédois/Swedish": "sv", "Swahili": "sw",
    "Tamoul": "ta", "Telugu": "te", "Thaï": "th", "Tagalog": "tl",
    "Turc": "tr", "Ukrainian": "uk", "Ourdou/Urdu": "ur", "Vietnamien": "vi",
    "Zoulou": "zu", "Persan / Farsi": "fa",
}

google_langs = set(langues_disponibles.values()) | {"cs", "eo"}


def traduire_texte(text, src="auto", dest="en"):
    try:
        return GoogleTranslator(source=src, target=dest).translate(text)
    except Exception as e:
        print(f"Erreur traduction ({src} → {dest}) : {e}")
        return text


def lire_audio(text, langue="fr"):
    """Génère (ou récupère en cache) un fichier audio WAV pour le texte."""
    if not text or not text.strip() or langue not in google_langs:
        return None
    filename = hashlib.md5(f"{langue}_{text}".encode()).hexdigest() + ".wav"
    if os.path.exists(filename):
        return filename
    try:
        temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        gTTS(text=text, lang=langue).save(temp_mp3)
        AudioSegment.from_file(temp_mp3, format="mp3").export(filename, format="wav")
        os.remove(temp_mp3)
        return filename
    except Exception as e:
        print(f"Erreur TTS ({langue}) : {e}")
        return None


def afficher_audio(text, langue):
    path = lire_audio(text, langue)
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            st.audio(f.read(), format="audio/wav")


def transcrire_audio(file_path, langue="fr"):
    try:
        r = sr.Recognizer()
        with sr.AudioFile(file_path) as source:
            audio_data = r.record(source)
        return r.recognize_google(audio_data, language=langue)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return "Failed to connect to the service."
    except Exception as e:
        return f"Erreur de transcription : {e}"


def get_local_datetime():
    try:
        return datetime.now(pytz.timezone("Africa/Lome")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "date/heure inconnue"


# ============================================================
# SESSION & CONVERSATIONS
# ============================================================
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

SAVE_FILE = f"conversation_{st.session_state.user_id}.json"

if os.path.exists(SAVE_FILE):
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        all_conversations = json.load(f)
else:
    all_conversations = {}

if "current_chat" not in st.session_state:
    if all_conversations:
        st.session_state.current_chat = list(all_conversations.keys())[0]
    else:
        st.session_state.current_chat = str(uuid.uuid4())

if st.session_state.current_chat not in all_conversations:
    all_conversations[st.session_state.current_chat] = []

conversation = all_conversations[st.session_state.current_chat]


def save_conversations():
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(all_conversations, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde : {e}")


def get_history():
    """Convertit la conversation en paires (question, réponse) pour le LLM."""
    pairs, pending = [], None
    for msg in conversation:
        if msg["role"] == "user":
            pending = msg["content"]
        elif msg["role"] == "assistant" and pending is not None:
            pairs.append((pending, msg["content"]))
            pending = None
    return pairs


USER_AVATAR = "https://upload.wikimedia.org/wikipedia/commons/7/70/User_icon_BLACK-01.png"
BOT_AVATAR = "https://upload.wikimedia.org/wikipedia/commons/8/89/Portrait_Placeholder.png"

# ============================================================
# BARRE LATÉRALE
# ============================================================
st.sidebar.markdown("<h1 style='color:#3498db;'>Agent conversationnel</h1>", unsafe_allow_html=True)
st.sidebar.markdown("<h1 style='color:#f39c12;'>AI LANGUAGE</h1>", unsafe_allow_html=True)
st.sidebar.header("⚙️ Settings")

choix_langue = st.sidebar.selectbox("🌍 LANGUAGES", list(langues_disponibles.keys()))
langue_cible = langues_disponibles[choix_langue]

uploaded_file = st.sidebar.file_uploader("📁", type=["pdf", "xlsx", "xls", "csv", "txt", "docx"])

st.sidebar.markdown("---")
if st.sidebar.button("➕ New chat"):
    new_id = str(uuid.uuid4())
    all_conversations[new_id] = []
    st.session_state.current_chat = new_id
    save_conversations()
    st.rerun()

for chat_id, messages in all_conversations.items():
    titre = "Chat"
    ts = ""
    for msg in messages:
        if msg["role"] == "user" and msg["content"].strip():
            titre = msg["content"][:30] + ("..." if len(msg["content"]) > 30 else "")
            ts = msg.get("timestamp", "")
            break
    label = f"{titre} ({ts})" if ts else titre
    if st.sidebar.button(label, key=chat_id):
        st.session_state.current_chat = chat_id
        st.rerun()

# ============================================================
# AFFICHAGE DE LA CONVERSATION
# ============================================================
for msg in conversation:
    avatar = USER_AVATAR if msg["role"] == "user" else BOT_AVATAR
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"], unsafe_allow_html=True)


def repondre(question, source_label=None):
    """Génère, traduit, affiche, lit à voix haute et sauvegarde la réponse."""
    history = get_history()
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        placeholder = st.empty()
        reponse = get_answer(question, history, placeholder)
        texte_final = traduire_texte(reponse, dest=langue_cible) if langue_cible != "fr" else reponse
        placeholder.markdown(texte_final)
        afficher_audio(texte_final, langue_cible)
    conversation.append({"role": "assistant", "content": texte_final, "timestamp": get_local_datetime()})
    save_conversations()


# ============================================================
# ENTRÉE VOCALE
# ============================================================
_, col2, _ = st.columns([1, 2, 1])
with col2:
    audio_input = st.audio_input("Speak now")

if audio_input is not None:
    audio_bytes = audio_input.getvalue()
    audio_id = hashlib.md5(audio_bytes).hexdigest()
    if st.session_state.get("last_audio_id") != audio_id:
        st.session_state.last_audio_id = audio_id

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp.write(audio_bytes)
        tmp.close()

        texte_transcrit = transcrire_audio(tmp.name, langue=langue_cible)
        os.remove(tmp.name)

        st.markdown("<h1 style='text-align:center;color:#27ae60;'>Transcription</h1>", unsafe_allow_html=True)
        st.info(texte_transcrit)

        if texte_transcrit.strip():
            conversation.append({"role": "user", "content": texte_transcrit, "timestamp": get_local_datetime()})
            with st.spinner("Réflexion en cours..."):
                repondre(texte_transcrit)

# ============================================================
# ANALYSE DE FICHIER
# ============================================================
if uploaded_file:
    st.sidebar.success(f"Fichier chargé : {uploaded_file.name}")
    file_key = f"{uploaded_file.name}_{uploaded_file.size}"

    if st.session_state.get("last_file") != file_key:
        st.session_state.last_file = file_key
        ext = uploaded_file.name.split(".")[-1].lower()
        texte = ""
        try:
            if ext == "pdf":
                texte = "\n".join((p.extract_text() or "") for p in PdfReader(uploaded_file).pages)
            elif ext in ("xlsx", "xls"):
                texte = pd.read_excel(uploaded_file).to_string()
            elif ext == "csv":
                texte = pd.read_csv(uploaded_file).to_string()
            elif ext == "txt":
                texte = uploaded_file.read().decode("utf-8")
            elif ext == "docx":
                texte = "\n".join(p.text for p in docx.Document(uploaded_file).paragraphs)

            if texte.strip():
                with st.spinner("Analyse en cours..."):
                    prompt_fichier = f"Analyse et résume ce document :\n\n{texte[:12000]}"
                    brute = get_answer(prompt_fichier, get_history())
                    reponse = latex_to_text(brute)
                    final = traduire_texte(reponse, dest=langue_cible) if langue_cible != "fr" else reponse

                    conversation.append({"role": "assistant", "content": final, "timestamp": get_local_datetime()})
                    with st.chat_message("assistant", avatar=BOT_AVATAR):
                        st.markdown(final)
                        afficher_audio(final, langue_cible)
                    save_conversations()
            else:
                st.warning("Aucun texte exploitable dans ce fichier.")
        except Exception as e:
            st.error(f"Erreur lors du traitement du fichier : {e}")

# ============================================================
# ENTRÉE TEXTE
# ============================================================
if prompt := st.chat_input("Ask Yanfudaan Now"):
    conversation.append({"role": "user", "content": prompt, "timestamp": get_local_datetime()})
    st.chat_message("user", avatar=USER_AVATAR).markdown(prompt)
    with st.spinner("Réflexion..."):
        try:
            repondre(prompt)
        except Exception as e:
            st.error(f"{e}")

save_conversations()
