import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

st.set_page_config(
    page_title="Zoek App",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("🔍 Zoek App")
st.write("Voer een zoekterm in en krijg 10 URL links")

def search_duckduckgo(query, num_results=10):
    """Zoek op DuckDuckGo en haal URL's op"""
    try:
        from urllib.parse import unquote, parse_qs, urlparse
        
        url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for result in soup.find_all('a', class_='result__a', limit=num_results):
            href = result.get('href')
            if href and isinstance(href, str) and '?' in href:
                parsed = parse_qs(urlparse(href).query)
                if 'uddg' in parsed:
                    actual_url = unquote(parsed['uddg'][0])
                    results.append(actual_url)
        
        return results
    except Exception as e:
        raise Exception(f"Fout bij zoeken: {str(e)}")

zoekterm = st.text_input("Wat wil je zoeken?", placeholder="Bijvoorbeeld: beste restaurants Amsterdam")

if st.button("Zoeken", type="primary", use_container_width=True):
    if zoekterm:
        with st.spinner("Zoeken..."):
            try:
                resultaten = search_duckduckgo(zoekterm, 10)
                
                if resultaten:
                    st.success(f"✅ {len(resultaten)} resultaten gevonden!")
                    st.write("---")
                    
                    for i, url in enumerate(resultaten, 1):
                        st.write(f"**{i}.** {url}")
                else:
                    st.warning("Geen resultaten gevonden. Probeer een andere zoekterm.")
            except Exception as e:
                st.error(f"Er is een fout opgetreden: {str(e)}")
                st.info("Probeer het opnieuw over een paar seconden.")
    else:
        st.warning("⚠️ Voer eerst een zoekterm in!")

st.write("---")
st.caption("💡 Tip: Deze app werkt ook op je mobiele telefoon!")
