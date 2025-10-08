import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse
import socket
import time

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

# ---------- SESSION STATE ----------
if "resultaten" not in st.session_state:
    st.session_state.resultaten = []
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "max_results" not in st.session_state:
    st.session_state.max_results = 10

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

# ---------- FUNCTIE VOOR ZOEKEN MET SELENIUM ----------
def run_search_selenium(query, max_results=30):
    if not internet_beschikbaar():
        st.warning("📡 Geen internetverbinding.")
        return []

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

    driver.get(f"https://duckduckgo.com/?q={query}")

    time.sleep(2)  # laat de pagina laden

    results = []
    while len(results) < max_results:
        nodes = driver.find_elements(By.CSS_SELECTOR, ".result__a")
        for r in nodes[len(results):max_results]:
            try:
                url = r.get_attribute("href")
                title = r.text
                domain = urlparse(url).netloc.replace("www.", "")
                favicon = f"https://www.google.com/s2/favicons?domain={domain}" if domain else ""
                full_title = f"{title} – {domain}" if domain else title
                results.append({"url": url, "title": full_title, "favicon": favicon})
            except Exception:
                continue
        # Probeer scrollen om nieuwe resultaten te laden
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(2)
        if len(nodes) >= max_results:
            break

    driver.quit()
    return results

# ---------- ACTIES ----------
if search_clicked:
    if not zoekterm.strip():
        st.warning("⚠️ Voer eerst een zoekterm in!")
    else:
        with st.spinner("Zoeken..."):
            resultaten = run_search_selenium(zoekterm.strip(), max_results=30)
            if resultaten:
                st.session_state.resultaten = resultaten[:10]
                st.session_state.last_query = zoekterm.strip()
                st.session_state.max_results = 10
            else:
                st.warning("Geen resultaten gevonden of DuckDuckGo blokkeert het verkeer.")

if more_clicked:
    if not st.session_state.resultaten:
        st.warning("🔎 Zoek eerst iets voordat je meer resultaten opvraagt.")
    else:
        # Toon 10 extra resultaten als beschikbaar
        nieuwe_max = st.session_state.max_results + 10
        st.session_state.max_results = min(len(st.session_state.resultaten) + 10, 30)
        st.session_state.resultaten = run_search_selenium(
            st.session_state.last_query,
            max_results=st.session_state.max_results
        )

# ---------- RESULTAAT WEERGAVE ----------
resultaten = st.session_state.resultaten

if resultaten:
    st.success(f"✅ {len(resultaten)} resultaten voor: {st.session_state.last_query}")
    st.markdown("### 🌐 Zoekresultaten")
    st.divider()
    for i, r in enumerate(resultaten, 1):
        favicon_html = f"<img src='{r['favicon']}' style='width:16px;height:16px;margin-right:5px;'>" if r['favicon'] else ""
        url = r.get("url", "")
        title = r.get("title", url)
        st.markdown(f"{favicon_html} **{i}. [{title}]({url})**", unsafe_allow_html=True)

    st.divider()
    st.markdown("🧠 **AI-samenvatting (binnenkort beschikbaar)**")
    st.info("Hier komt later een korte samenvatting van de gevonden pagina’s.")
else:
    st.info("Voer een zoekterm in en klik op 🔎 Zoeken om resultaten te zien.")

st.caption("💡 Tip: Voeg deze app toe aan je beginscherm op iPhone voor snelle toegang!")