import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse
import socket

# ---------- PAGINA INSTELLINGEN ----------
st.set_page_config(
    page_title="Zoek App",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ---------- THEME / DARK MODE ----------
dark_mode = st.sidebar.checkbox("🌙 Dark Mode", value=False)
if dark_mode:
    st.markdown("""
        <style>
        .main { background-color: #1e1e1e; color: #f0f0f0; }
        a { color: #1E90FF; }
        </style>
    """, unsafe_allow_html=True)

st.title("🔍 Zoek App")
st.write("Voer een zoekterm in en krijg betrouwbare zoekresultaten met favicon, domein en waarschuwing bij verdachte sites.")

# ---------- INTERNET CHECK ----------
def internet_beschikbaar():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

# ---------- DUCKDUCKGO ZOEK ----------
def search_duckduckgo(query, max_results=30):
    """Probeer resultaten op te halen via DuckDuckGo HTML."""
    try:
        url = f"https://duckduckgo.com/html/?q={quote(query)}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        for r in soup.select(".result__a")[:max_results]:
            link = r.get("href")
            if not link or not link.startswith("http"):
                continue
            title = r.get_text(strip=True)
            domain = urlparse(link).netloc.replace("www.", "")
            full_title = f"{title} – {domain}" if domain else title
            favicon = f"https://www.google.com/s2/favicons?domain={domain}" if domain else ""
            suspicious = not any(domain.endswith(ext) for ext in [".com", ".org", ".net", ".nl"])
            results.append({"url": link, "title": full_title, "favicon": favicon, "suspicious": suspicious})
        return results
    except Exception as e:
        raise ConnectionError(f"DuckDuckGo niet bereikbaar ({e})")

# ---------- BRAVE SEARCH (HTML) ----------
def search_brave(query, max_results=20):
    """Fallback: Brave Search (HTML)."""
    url = f"https://search.brave.com/search?q={quote(query)}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    for r in soup.select("a.result-header")[:max_results]:
        link = r.get("href")
        title = r.get_text(strip=True)
        domain = urlparse(link).netloc.replace("www.", "")
        full_title = f"{title} – {domain}" if domain else title
        favicon = f"https://www.google.com/s2/favicons?domain={domain}" if domain else ""
        suspicious = not any(domain.endswith(ext) for ext in [".com", ".org", ".net", ".nl"])
        results.append({"url": link, "title": full_title, "favicon": favicon, "suspicious": suspicious})
    return results

# ---------- WIKIPEDIA FALLBACK ----------
def search_wikipedia(query, max_results=10):
    """Fallback: Wikipedia (vereenvoudigde zoekfunctie)."""
    url = f"https://en.wikipedia.org/w/index.php?search={quote(query)}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    for r in soup.select(".mw-search-result-heading a")[:max_results]:
        link = "https://en.wikipedia.org" + r.get("href")
        title = r.get_text(strip=True)
        domain = "wikipedia.org"
        favicon = f"https://www.google.com/s2/favicons?domain={domain}"
        results.append({"url": link, "title": f"{title} – {domain}", "favicon": favicon, "suspicious": False})
    return results

# ---------- SESSION STATE ----------
if "resultaten" not in st.session_state:
    st.session_state.resultaten = []
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "num_results" not in st.session_state:
    st.session_state.num_results = 10

# ---------- UI ----------
zoekterm = st.text_input(
    "Wat wil je zoeken?",
    placeholder="Bijvoorbeeld: beste restaurants Amsterdam",
    value=st.session_state.get("last_query", "")
)

tijd_filter = st.selectbox("⏰ Tijd filteren (werkt binnenkort)", ["Alles", "Afgelopen dag", "Afgelopen week", "Afgelopen maand"])

col1, col2 = st.columns([4, 1])
with col1:
    search_clicked = st.button("🔎 Zoeken", use_container_width=True)
with col2:
    more_clicked = st.button("🔄 Toon meer", use_container_width=True)

# ---------- ACTIES ----------
if search_clicked:
    if not zoekterm.strip():
        st.warning("⚠️ Voer eerst een zoekterm in!")
    elif not internet_beschikbaar():
        st.warning("📡 Geen internetverbinding.")
    else:
        with st.spinner("Zoeken..."):
            try:
                resultaten = search_duckduckgo(zoekterm.strip(), max_results=30)
            except Exception:
                try:
                    st.info("🦁 DuckDuckGo niet bereikbaar — overschakelen naar Brave Search...")
                    resultaten = search_brave(zoekterm.strip(), max_results=20)
                except Exception:
                    st.info("📚 Brave ook niet beschikbaar — overschakelen naar Wikipedia...")
                    resultaten = search_wikipedia(zoekterm.strip(), max_results=10)

            st.session_state.resultaten = resultaten
            st.session_state.last_query = zoekterm.strip()
            st.session_state.num_results = 10

if more_clicked:
    if st.session_state.resultaten:
        st.session_state.num_results = min(
            st.session_state.num_results + 10, len(st.session_state.resultaten)
        )
    else:
        st.warning("🔎 Zoek eerst iets voordat je meer resultaten opvraagt.")

# ---------- RESULTATEN TONEN ----------
resultaten = st.session_state.resultaten[:st.session_state.num_results]
totaal = len(st.session_state.resultaten)

if resultaten:
    st.success(f"✅ {len(resultaten)} resultaten getoond van {totaal} voor: {st.session_state.last_query}")
    st.progress(len(resultaten)/totaal if totaal > 0 else 0)
    st.markdown("### 🌐 Zoekresultaten")
    st.divider()

    for i, r in enumerate(resultaten, 1):
        favicon_html = f"<img src='{r['favicon']}' style='width:16px;height:16px;margin-right:5px;'>" if r['favicon'] else ""
        suspicious_label = " ⚠️" if r['suspicious'] else ""
        st.markdown(f"{favicon_html} **{i}. [{r['title']}]({r['url']})**{suspicious_label}", unsafe_allow_html=True)

    st.divider()
    st.markdown("🧠 **AI-samenvatting (binnenkort beschikbaar)**")
    st.info("Hier komt later een korte samenvatting van de gevonden pagina’s.")
else:
    st.info("Voer een zoekterm in en klik op 🔎 Zoeken om resultaten te zien.")

st.caption("💡 Tip: Voeg deze app toe aan je iPhone-beginscherm voor snelle toegang!")