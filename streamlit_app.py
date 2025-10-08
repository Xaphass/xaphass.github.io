import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote, parse_qs, urlparse
import socket

# ---------- PAGINA INSTELLINGEN ----------
st.set_page_config(
    page_title="Zoek App",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("🔍 Zoek App")
st.write("Voer een zoekterm in en krijg gestructureerde zoekresultaten met titels, domein en favicon.")

# ---------- INTERNET CHECK ----------
def internet_beschikbaar():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

# ---------- HELPER: haal echte URL uit DuckDuckGo-href ----------
def extract_actual_url(href):
    if not href or not isinstance(href, str):
        return None
    try:
        p = urlparse(href)
        qs = parse_qs(p.query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
        if href.startswith("http"):
            return href
        if "uddg=" in href:
            after = href.split("uddg=", 1)[1]
            actual = after.split("&")[0]
            return unquote(actual)
    except Exception:
        return None
    return None

# ---------- FUNCTIE MET CACHING ----------
@st.cache_data(ttl=600)
def search_duckduckgo(query):
    """Zoek op DuckDuckGo en haal max 30 resultaten op."""
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    text = resp.text or ""
    if "unusual traffic" in text.lower():
        raise RuntimeError("DuckDuckGo blokkeert verkeer. Probeer het later.")

    soup = BeautifulSoup(text, "html.parser")
    results = []
    for node in soup.select('.result'):
        try:
            title_el = node.select_one('.result__a') or node.find('a')
            if not title_el:
                continue
            href = title_el.get("href")
            actual = extract_actual_url(href)
            if not actual:
                continue
            title_text = title_el.get_text(" ", strip=True) or actual
            snippet_el = node.select_one('.result__snippet')
            snippet_text = snippet_el.get_text(" ", strip=True) if snippet_el else ''
            domain = urlparse(actual).netloc.replace("www.", "")
            full_title = f"{title_text} – {domain}" if domain else title_text
            # favicon URL
            favicon = f"https://www.google.com/s2/favicons?domain={domain}" if domain else ""
            results.append({"url": actual, "title": full_title, "snippet": snippet_text, "favicon": favicon})
        except Exception:
            continue
        if len(results) >= 30:
            break
    return results

# ---------- SESSION STATE ----------
if "resultaten" not in st.session_state:
    st.session_state.resultaten = []
if "last_query" not in st.session_state:
    st.session_state.last_query = ""

# ---------- UI ----------
zoekterm = st.text_input(
    "Wat wil je zoeken?",
    placeholder="Bijvoorbeeld: beste restaurants Amsterdam",
    value=st.session_state.get("last_query", "")
)

search_clicked = st.button("🔎 Zoeken", use_container_width=True)

# ---------- ACTIES ----------
def run_search(query):
    if not internet_beschikbaar():
        st.warning("📡 Geen internetverbinding. Controleer je verbinding.")
        return
    try:
        resultaten = search_duckduckgo(query)
        st.session_state.resultaten = resultaten
        st.session_state.last_query = query
    except requests.exceptions.RequestException:
        st.warning("📡 Geen internet of server niet bereikbaar.")
    except RuntimeError as re:
        st.error(str(re))
    except Exception as e:
        st.error(f"Er is iets misgegaan: {str(e)}")

if search_clicked:
    if not zoekterm.strip():
        st.warning("⚠️ Voer eerst een zoekterm in!")
    else:
        run_search(zoekterm.strip())

# ---------- RESULTAAT WEERGAVE ----------
resultaten = st.session_state.resultaten

if resultaten:
    st.success(f"✅ {len(resultaten)} resultaten voor: {st.session_state.last_query}")
    st.markdown("### 🌐 Zoekresultaten")
    st.divider()
    for i, r in enumerate(resultaten, 1):
        favicon = r.get("favicon")
        favicon_html = f"<img src='{favicon}' style='width:16px;height:16px;margin-right:5px;'>" if favicon else ""
        url = r.get("url", "")
        title = r.get("title", url)
        snippet = r.get("snippet", "")
        st.markdown(f"{favicon_html} **{i}. [{title}]({url})**  \n{snippet}", unsafe_allow_html=True)

    st.divider()
    st.markdown("🧠 **AI-samenvatting (binnenkort beschikbaar)**")
    st.info("Hier komt later een korte samenvatting van de gevonden pagina’s.")
else:
    st.info("Voer een zoekterm in en klik op 🔎 Zoeken om resultaten te zien.")

st.caption("💡 Tip: Voeg deze app toe aan je beginscherm op iPhone voor snelle toegang!")