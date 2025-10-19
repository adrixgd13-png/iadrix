import streamlit as st
import requests
from sympy import sympify
import time
import wikipedia
import re

# ---------------------------
# ⚙️ CONFIG STREAMLIT
# ---------------------------
st.set_page_config(page_title="IAdrix 💻", layout="wide")
st.markdown("""
<style>
body {background-color: white; color: #00AA00; font-family: monospace;}
.stTextInput>div>div>input {background-color: white; color: #00AA00; font-family: monospace;}
.stButton>button {background-color: #111; color: #00AA00; font-family: monospace;}
div.stScrollView > div {scroll-behavior: smooth;}
</style>
""", unsafe_allow_html=True)
st.title("IAdrix 💻")

# ---------------------------
# 🧠 MÉMOIRE DE CONVERSATION
# ---------------------------
if "history" not in st.session_state:
    st.session_state.history = []

# ---------------------------
# 🔢 OUTILS UTILES
# ---------------------------
def calculer(expr):
    try:
        return str(sympify(expr).evalf())
    except Exception:
        return "Erreur dans le calcul"

def est_calcul(expr):
    return all(c in "0123456789+-*/(). " for c in expr.strip())

def get_weather(city):
    try:
        geo = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1").json()
        if "results" not in geo or len(geo["results"]) == 0:
            return "Ville introuvable."
        lat, lon = geo["results"][0]["latitude"], geo["results"][0]["longitude"]
        city_name = geo["results"][0].get("name", city)
        m = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto").json()
        cw = m.get("current_weather", {})
        if not cw:
            return "Pas de données météo."
        return f"{city_name} — {cw['temperature']}°C, vent {cw['windspeed']} km/h"
    except Exception:
        return "Erreur météo"

def recherche_wiki(query):
    try:
        wikipedia.set_lang("fr")
        search_hits = wikipedia.search(query, results=5)
        if not search_hits:
            return "Aucun résultat Wikipédia trouvé."
        try:
            title = search_hits[0]
            summary = wikipedia.summary(title, sentences=3)
            return f"Wikipedia — {title} :\n\n{summary}"
        except wikipedia.DisambiguationError as e:
            options = e.options[:5]
            return "Résultat ambigu sur Wikipédia. Précise ta recherche :\n" + "\n".join(f"- {opt}" for opt in options)
        except Exception:
            return "Problème avec Wikipédia pour ce sujet."
    except Exception:
        return "Erreur recherche Wikipédia."

def afficher_texte_animation(texte, vitesse=0.02):
    affichage = ""
    placeholder = st.empty()
    for lettre in texte:
        affichage += lettre
        placeholder.text(f"IAdrix : {affichage}")
        time.sleep(vitesse)
    placeholder.empty()

def nettoie_reponse_du_role(text):
    patterns = [
        r"Je suis IAdrix[^\.\n]*[\.!\?]?",
        r"Tu es IAdrix[^\.\n]*[\.!\?]?",
        r"Je suis un assistant[^\.\n]*[\.!\?]?",
        r"Je peux être sérieux[^\.\n]*[\.!\?]?"
    ]
    cleaned = text
    for p in patterns:
        cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE)
    if len(cleaned.strip()) < 10:
        return text.strip()
    return re.sub(r"\s{2,}", " ", cleaned).strip()

# ---------------------------
# 🧠 FONCTION IA (MISTRAL)
# ---------------------------
def obtenir_reponse_ia(question, echo_mode=False):
    api_key = "yzmNsxBU31PkKWs7v4EGkbUeiLZvplpU"
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    if echo_mode:
        messages = [{"role": "system", "content": "Répète exactement ce que l'utilisateur dit, sans rien ajouter."}]
    else:
        messages = [{"role": "system", "content": (
            "Tu es IAdrix, un pote virtuel drôle, curieux et naturel. "
            "Tu réponds simplement, sans phrases de présentation inutiles. "
            "Sois amical, un peu taquin, mais clair. "
            "Si tu ne sais pas quelque chose, dis-le honnêtement et propose d'utiliser la commande 'cherche <sujet>'."
            "adapte toi au language de l'utilisateur"
        )}]

    # Ajoute les 20 derniers messages pour garder le contexte
    for msg in st.session_state.history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": question})
    data = {"model": "open-mixtral-8x22b", "messages": messages}

    try:
        response = requests.post(url, json=data, headers=headers, timeout=20)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content'].strip()
            content = nettoie_reponse_du_role(content)
            st.session_state.history.append({"role": "assistant", "content": content})
            return content
        else:
            return f"Erreur API {response.status_code}"
    except Exception as e:
        return f"Erreur API: {e}"

# ---------------------------
# 💬 INPUT UTILISATEUR
# ---------------------------
texte = st.text_input("Vous :", value="", key="input_text")
envoyer = st.button("Envoyer")

# ---------------------------
# 🧩 LOGIQUE PRINCIPALE
# ---------------------------
if envoyer and texte:
    st.session_state.history.append({"role": "user", "content": texte})
    cmd = texte.lower().strip()

    # Mode "répète après moi"
    if "répète après moi" in cmd or "repete apres moi" in cmd:
        echo_mode = True
        parts = re.split(r"après moi|apres moi", texte, flags=re.IGNORECASE)
        texte_a_repeater = parts[-1].strip() if len(parts) > 1 and parts[-1].strip() else texte
    else:
        echo_mode = False
        texte_a_repeater = texte

    # Commandes spéciales
    if cmd.startswith("calc ") or est_calcul(texte):
        res = calculer(texte[5:].strip() if cmd.startswith("calc ") else texte)
        assistant_text = f"Résultat → {res}"
        st.session_state.history.append({"role": "assistant", "content": assistant_text})
        afficher_texte_animation(assistant_text)

    elif cmd.startswith("meteo "):
        ville = texte[6:].strip()
        meteo = get_weather(ville)
        st.session_state.history.append({"role": "assistant", "content": meteo})
        afficher_texte_animation(meteo)

    elif cmd.startswith("cherche ") or cmd.startswith("qui est "):
        query = re.sub(r'^(cherche|qui est)\s+', '', texte, flags=re.IGNORECASE).strip()
        res = recherche_wiki(query)
        st.session_state.history.append({"role": "assistant", "content": res})
        afficher_texte_animation(res)

    else:
        ia_res = obtenir_reponse_ia(texte_a_repeater, echo_mode=echo_mode)
        afficher_texte_animation(ia_res)

# ---------------------------
# 📜 AFFICHAGE DE L’HISTORIQUE
# ---------------------------
for msg in st.session_state.history:
    prefix = "Vous : " if msg["role"] == "user" else "IAdrix : "
    st.text(prefix + msg["content"])

st.markdown("<script>window.scrollTo(0, document.body.scrollHeight);</script>", unsafe_allow_html=True)
