import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse
import socket

# ---------- PAGINA INSTELLINGEN ----------
st.set_page_config(
    page_title="Zoek App",
    page_icon="🔍",
    layout="centered"
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

# ---------- HELPER: resultaten ophalen ----------
def search_duckduckgo(query, max_results=30):
    """Haalt resultaten op via DuckDuckGo HTML."""
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    headers = {'User-Agent': 'Mozilla/5.0'}

    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for r in soup.select(".result__a")[:max_results]:
        try:
            link = r.get("href")
            if not link.startswith("http"):
                continue
            title = r.get_text(strip=True)
            domain = urlparse(link).netloc.replace("www.", "")
            full_title = f"{title} – {domain}" if domain else title
            favicon = f"https://www.google.com/s2/favicons?domain={domain}" if domain else ""
            results.append({"url": link, "title": full_title, "favicon": favicon})
        except:
            continue
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
                if resultaten:
                    st.session_state.resultaten = resultaten
                    st.session_state.last_query = zoekterm.strip()
                    st.session_state.num_results = 10
                else:
                    st.warning("Geen resultaten gevonden.")
            except Exception as e:
                st.error(f"Er is een fout opgetreden: {str(e)}")

if more_clicked:
    if st.session_state.resultaten:
        st.session_state.num_results = min(st.session_state.num_results + 10, len(st.session_state.resultaten))
    else:
        st.warning("🔎 Zoek eerst iets voordat je meer resultaten opvraagt.")

# ---------- RESULTAAT WEERGAVE ----------
resultaten = st.session_state.resultaten[:st.session_state.num_results]

if resultaten:
    st.success(f"✅ {len(resultaten)} resultaten getoond voor: {st.session_state.last_query}")
    st.markdown("### 🌐 Zoekresultaten")
    st.divider()
    for i, r in enumerate(resultaten, 1):
        favicon_html = f"<img src='{r['favicon']}' style='width:16px;height:16px;margin-right:5px;'>" if r['favicon'] else ""
        st.markdown(f"{favicon_html} **{i}. [{r['title']}]({r['url']})**", unsafe_allow_html=True)

    st.divider()
    st.markdown("🧠 **AI-samenvatting (binnenkort beschikbaar)**")
    st.info("Hier komt later een korte samenvatting van de gevonden pagina’s.")
else:
    st.info("Voer een zoekterm in en klik op 🔎 Zoeken om resultaten te zien.")

st.caption("💡 Tip: Voeg deze app toe aan je beginscherm op iPhone voor snelle toegang!")