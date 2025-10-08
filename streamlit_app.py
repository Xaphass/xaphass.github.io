import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote, parse_qs, urlparse

# ---------- PAGINA INSTELLINGEN ----------
st.set_page_config(
    page_title="Zoek App",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("🔍 Zoek App")
st.write("Voer een zoekterm in en krijg 10 URL's met titel en korte beschrijving.")

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
                results.append({
                    "url": actual_url,
                    "title": title,
                    "snippet": snippet
                })

    return results

# ---------- UI ----------
zoekterm = st.text_input(
    "Wat wil je zoeken?",
    placeholder="Bijvoorbeeld: beste restaurants Amsterdam"
)

if st.button("🔎 Zoeken", type="primary", use_container_width=True):
    if zoekterm:
        with st.spinner("Even geduld, zoeken..."):
            try:
                resultaten = search_duckduckgo(zoekterm, 10)

                if resultaten:
                    st.success(f"✅ {len(resultaten)} resultaten gevonden!")
                    st.markdown("### 🌐 Zoekresultaten")
                    st.divider()

                    for i, r in enumerate(resultaten, 1):
                        st.markdown(
                            f"**{i}. [{r['title']}]({r['url']})**  \n{r['snippet']}",
                            unsafe_allow_html=True
                        )
                else:
                    st.warning("Geen resultaten gevonden. Probeer een andere zoekterm.")
            except Exception as e:
                st.error(f"Er is een fout opgetreden: {str(e)}")
                st.info("Probeer het opnieuw over een paar seconden.")
    else:
        st.warning("⚠️ Voer eerst een zoekterm in!")

st.divider()
st.caption("💡 Tip: Deze app werkt ook goed op mobiele telefoons!")