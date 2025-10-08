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
st.write("Voer een zoekterm in en krijg gestructureerde zoekresultaten met titels, snippets en domeinnaam.")

# ---------- INTERNET CHECK ----------
def internet_beschikbaar():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

# ---------- FUNCTIE MET CACHING ----------
@st.cache_data(ttl=600)
def search_duckduckgo(query, num_results=10):
    """Zoek op DuckDuckGo en haal titels, snippets en URL's op."""
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    results = []

    for result in soup.select('.result', limit=num_results):
        title_el = result.select_one('.result__a')
        snippet_el = result.select_one('.result__snippet')
        if title_el:
            href = title_el.get('href')
            parsed = parse_qs(urlparse(href).query)
            if 'uddg' in parsed:
                actual_url = unquote(parsed['uddg'][0])
                title = title_el.text.strip()
                snippet = snippet_el.text.strip() if snippet_el else ''
                # Domeinnaam extraheren
                domain = urlparse(actual_url).netloc.replace("www.", "")
                results.append({
                    "url": actual_url,
                    "title": f"{title} – {domain}",
                    "snippet": snippet
                })

    return results

# ---------- INITIAL STATE ----------
if "num_results" not in st.session_state:
    st.session_state.num_results = 10

# ---------- UI ----------
zoekterm = st.text_input(
    "Wat wil je zoeken?",
    placeholder="Bijvoorbeeld: beste restaurants Amsterdam"
)

col1, col2 = st.columns([4, 1])
with col1:
    zoeken = st.button("🔎 Zoeken", use_container_width=True)
with col2:
    meer = st.button("🔄 Toon meer resultaten", use_container_width=True)

# ---------- LOGICA ----------
if zoeken:
    if not internet_beschikbaar():
        st.warning("📡 Geen internetverbinding. Controleer je verbinding en probeer opnieuw.")
    elif zoekterm:
        with st.spinner("Even geduld, zoeken..."):
            try:
                resultaten = search_duckduckgo(zoekterm, st.session_state.num_results)

                if resultaten:
                    st.success(f"✅ {len(resultaten)} resultaten gevonden!")
                    st.markdown("### 🌐 Zoekresultaten")
                    st.divider()

                    for i, r in enumerate(resultaten, 1):
                        st.markdown(
                            f"**{i}. [{r['title']}]({r['url']})**  \n{r['snippet']}",
                            unsafe_allow_html=True
                        )

                    # Placeholder voor toekomstige AI-samenvatting
                    st.divider()
                    st.markdown("🧠 **AI-samenvatting (binnenkort beschikbaar)**")
                    st.info("Hier komt later een automatische samenvatting van de gevonden pagina’s.")
                else:
                    st.warning("Geen resultaten gevonden. Probeer een andere zoekterm.")
            except requests.exceptions.RequestException:
                st.warning("📡 Geen internetverbinding of server onbereikbaar.")
            except Exception as e:
                st.error(f"Er is een fout opgetreden: {str(e)}")
                st.info("Probeer het opnieuw over een paar seconden.")
    else:
        st.warning("⚠️ Voer eerst een zoekterm in!")

elif meer:
    st.session_state.num_results += 10
    st.experimental_rerun()

st.divider()
st.caption("💡 Tip: Voeg deze app toe aan je beginscherm op iPhone voor snelle toegang!")