# 🌊 AQUAMIND / YANFUDAAN – AI Language Coach

Assistant vocal et conversationnel multilingue développé avec l'interface  **Streamlit**,


##  Fonctionnalités

- **Chat texte** avec historique de conversation sauvegardé (un fichier JSON par utilisateur).
-  **Entrée vocale** (`st.audio_input`) avec transcription via Google Speech Recognition.
-  **Réponse vocale** (gTTS) avec cache audio, lecture directement dans le chat.
-  **Plus de 60 langues** : sélection de la langue dans la barre latérale, traduction automatique des réponses (`deep-translator`) et réponse dans la langue de l'utilisateur.
-  **Analyse de fichiers** : PDF, Excel (`.xlsx`, `.xls`), CSV, TXT, DOCX.
-  **Calculs** basiques et avancés (SymPy).
- **Recherche** : Wikipédia, SerpAPI, Serper, Zenserp, ContextualWeb, Webit.
-  **Basculement automatique (fallback)** entre plusieurs modèles et fournisseurs :
  - DeepInfra (Llama 3.3 70B, DeepSeek R1, Qwen3 Coder, GLM-4.5, Mistral, gpt-oss…)
  - OpenRouter (Llama 3.1 405B, Gemini Flash, Nemotron, Qwen…)
  - DeepSeek (API officielle)
-  Nouveau chat / historique des conversations dans la barre latérale.
-  Serveur Flask « keep-alive » pour éviter la mise en veille sur Render.

---

## Technologies

| Domaine | Bibliothèques |
|---|---|
| Interface | Streamlit |
| Audio | PyAudio, pydub, SpeechRecognition, gTTS, soundfile |
| LLM / API | requests, OpenAI-compatible APIs (DeepInfra, OpenRouter, DeepSeek) |
| Recherche | wikipedia, google-search-results (SerpAPI) |
| Traduction | deep-translator, unidecode |
| Fichiers | PyPDF2, pandas, openpyxl, python-docx |
| Maths | SymPy |
| Géolocalisation / météo | geopy, geocoder, OpenWeatherMap |
| Divers | Flask, pytz, Pillow, BeautifulSoup4 |

---
##  Installation

### 1. Prérequis système

- Python 3.10+
- **FFmpeg** (requis par `pydub`)
- **PortAudio** (requis par `PyAudio`)

```bash
# Ubuntu / Debian
sudo apt install ffmpeg portaudio19-dev

# macOS
brew install ffmpeg portaudio
```

### 2. Cloner le projet et installer les dépendances

```bash
git clone <url-du-depot>
cd <nom-du-depot>
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

Exemple de `requirements.txt` :

```txt
streamlit
requests
sympy
pytz
pyaudio
pydub
SpeechRecognition
gTTS
soundfile
numpy
pandas
openpyxl
xlrd
Pillow
PyPDF2
python-docx
wikipedia
google-search-results
geopy
geocoder
beautifulsoup4
deep-translator
unidecode
flask
openai
accelerate
torch
```

---

## Configuration des clés API


Créez un fichier `.streamlit/secrets.toml` (à ajouter au `.gitignore`) :

```toml
OPENROUTER_API_KEY = "votre_cle"
DEEPINFRA_API_KEY  = "votre_cle"
DEEPSEEK_API_KEY   = "votre_cle"
SERP_API_KEY       = "votre_cle"
SERPER_KEY         = "votre_cle"
ZEN_SERP_KEY       = "votre_cle"
CONTEXTUALWEB_API_KEY = "votre_cle"
WEBIT_KEY          = "votre_cle"
OPENWEATHER_API_KEY = "votre_cle"
```

Puis dans le code : `st.secrets["OPENROUTER_API_KEY"]`.

---

##  Lancer l'application

```bash
streamlit run app.py
```

L'application est disponible sur `http://localhost:8501`.

---

##  Structure du projet

```
.
├── app.py                        # Application principale (Streamlit + Flask keep-alive)
├── abouaqu.jpg                   # Image du créateur
├── conversation_<user_id>.json   # Historique généré automatiquement
├── *.mp3 / *.wav                 # Cache audio généré automatiquement
├── requirements.txt
└── README.md
```

---

## Fonctionnement

1. L'utilisateur écrit un message ou parle au micro.
2. La voix est transcrite (Google Speech Recognition) dans la langue choisie.
3. La requête est envoyée successivement aux modèles (DeepInfra → OpenRouter → DeepSeek…) jusqu'à obtention d'une réponse valide.
4. En dernier recours : calcul, réponses prédéfinies, Wikipédia, puis moteurs de recherche.
5. La réponse est traduite si besoin, affichée, puis lue à voix haute (gTTS).
6. La conversation est sauvegardée en JSON.

---

##  Déploiement (Render)

- **Build command** : `pip install -r requirements.txt`
- **Start command** : `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- Ajoutez les clés API dans les *Environment Variables* de Render.
- Remplacez l'URL du `keep_alive()` par celle de votre service.

---

##  Points d'amélioration connus

- Clés API codées en dur dans le code (à déplacer vers des variables d'environnement).
- `PyAudio` et `torch` sont lourds et inutiles en déploiement cloud (l'enregistrement se fait via `st.audio_input`).
- Chaîne de fallback très longue et dupliquée (à factoriser dans une fonction unique).
- `eval()` dans `calcul_basique` : à remplacer par SymPy pour plus de sécurité.
- Fonctions dupliquées (`lire_audio`, `traduire_texte`) et doubles appels à `st.set_page_config`.
- Rôle vide (`""`) dans certains messages du chat : utiliser `"assistant"`.

---



