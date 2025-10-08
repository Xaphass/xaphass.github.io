# streamlit_app.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse, unquote, parse_qs
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import socket
import re
from collections import Counter

# ---------- PAGINA INSTELLINGEN ----------
st.set_page_config(
    page_title="Zoek App (Robuuste fallback)",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ---------- THEME / DARK MODE ----------
dark_mode = st.sidebar.checkbox("🌙 Dark Mode", value=False)
if dark_mode:
    st.markdown("""
        <style>
        .main { background-color: #121212; color: #e6e6e6; }
        a { color: #4EA1FF; }
        </style>
    """, unsafe_allow_html=True)

st.title("🔍 Zoek App")
st.write("Zoekt via DuckDuckGo → Brave → Wikipedia (fallbacks). Je ziet wél welke bron gebruikt is.")

# ---------- INTERNET CHECK ----------
def internet_beschikbaar():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

# ---------- REQUESTS SESSION MET RETRIES ----------
def make_session():
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=["GET", "HEAD"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36",
        "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://duckduckgo.com/"
    })
    return s

# ---------- HELPERS ----------
def extract_actual_url(href: str):
    """Haal echte URL uit DuckDuckGo-redirects (uddg) of return originele href."""
    if not href or not isinstance(href, str):
        return None
    try:
        p = urlparse(href)
        if p.query:
            qs = parse_qs(p.query)
            if "uddg" in qs:
                return unquote(qs["uddg"][0])
        # soms is href zelf al correct
        if href.startswith("http"):
            return href
        # fallback: zoek 'uddg=' substring
        if "uddg=" in href:
            after = href.split("uddg=", 1)[1].split("&")[0]
            return unquote(after)
    except Exception:
        return None
    return None

def parse_html_for_links(html: str, max_results: int = 30):
    """Algemene, defensieve parser: zoekt anchors in elementen met 'result' in class, anders alle anchors."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen = set()

    # zoek containers met 'result' of 'search' in classnaam
    candidate_containers = soup.find_all(attrs={'class': lambda x: x and ('result' in x.lower() or 'search' in x.lower() or 'item' in x.lower())})
    anchors = []
    for c in candidate_containers:
        anchors.extend(c.find_all('a', href=True))

    # als niks gevonden: fallback naar alle anchors in main content
    if not anchors:
        anchors = soup.find_all('a', href=True)

    for a in anchors:
        href = a.get('href')
        if not href:
            continue
        # probeer uddg -> echte url
        actual = extract_actual_url(href) or href
        if not actual.startswith("http"):
            continue
        title = a.get_text(" ", strip=True)
        if not title:
            # soms is title leeg; probeer title attrib of skip
            title = a.get('title') or ""
        if not title or len(title.strip()) < 2:
            continue
        # dedup
        if actual in seen:
            continue
        seen.add(actual)
        domain = urlparse(actual).netloc.replace("www.", "")
        favicon = f"https://www.google.com/s2/favicons?domain={domain}" if domain else ""
        suspicious = not any(domain.endswith(ext) for ext in ['.com', '.org', '.net', '.nl', '.edu'])
        full_title = f"{title} – {domain}" if domain else title
        results.append({
            "url": actual,
            "title": full_title,
            "favicon": favicon,
            "domain": domain,
            "suspicious": suspicious
        })
        if len(results) >= max_results:
            break
    return results

# ---------- ZOEKFUNCTIES MET FALLBACKS ----------
def search_duckduckgo(query, max_results=30, session=None):
    """Probeert meerdere DuckDuckGo endpoints; retourneert list of results of raises."""
    if session is None:
        session = make_session()
    endpoints = [
        f"https://duckduckgo.com/html/?q={quote(query)}",
        f"https://html.duckduckgo.com/html/?q={quote(query)}",
        f"https://duckduckgo.com/?q={quote(query)}"
    ]
    last_exc = None
    for ep in endpoints:
        try:
            r = session.get(ep, timeout=10)
            r.raise_for_status()
            results = parse_html_for_links(r.text, max_results=max_results)
            if results:
                return results, "DuckDuckGo", ep
        except Exception as e:
            last_exc = e
            # continue to next endpoint
            continue
    # niets gevonden of alle endpoints faalden
    raise ConnectionError(f"DuckDuckGo alle endpoints faalden: {last_exc}")

def search_brave(query, max_results=20, session=None):
    """Probeert Brave Search HTML (defensieve parser)."""
    if session is None:
        session = make_session()
    ep = f"https://search.brave.com/search?q={quote(query)}"
    try:
        r = session.get(ep, timeout=10)
        r.raise_for_status()
        results = parse_html_for_links(r.text, max_results=max_results)
        if results:
            return results, "Brave", ep
        # fallback empty list -> raise to trigger next fallback
        raise ConnectionError("Brave returned geen links")
    except Exception as e:
        raise ConnectionError(f"Brave faalde: {e}")

def search_wikipedia(query, max_results=10, session=None):
    """Gebruik de stabiele opensearch API van Wikipedia (JSON)."""
    if session is None:
        session = make_session()
    ep = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={quote(query)}&limit={max_results}&namespace=0&format=json"
    r = session.get(ep, timeout=10)
    r.raise_for_status()
    arr = r.json()
    titles = arr[1]
    links = arr[3]
    results = []
    for t, l in zip(titles, links):
        domain = "wikipedia.org"
        favicon = f"https://www.google.com/s2/favicons?domain={domain}"
        results.append({
            "url": l,
            "title": f"{t} – {domain}",
            "favicon": favicon,
            "domain": domain,
            "suspicious": False
        })
    if results:
        return results, "Wikipedia", ep
    raise ConnectionError("Wikipedia gaf geen resultaten")

# ---------- LOKALE 'AI' SAMENVATTING ----------
def generate_local_summary(results):
    if not results:
        return "Geen resultaten om samen te vatten."
    text = " ".join(r["title"] for r in results)
    words = re.findall(r"[a-zA-ZÀ-ÿ]{3,}", text.lower())
    stopwords = set([
        "the","and","for","with","that","you","are","this","from","your","how",
        "het","een","van","voor","met","dat","je","de","en","om","aan","bij",
        "die","zijn","niet","wat","kan","ook","als","hoe","waar","naar"
    ])
    filtered = [w for w in words if w not in stopwords]
    if not filtered:
        return "Geen duidelijke onderwerpen gevonden in de titels."
    common = [w for w, _ in Counter(filtered).most_common(5)]
    topics = ", ".join(common[:3])
    summary = (
        f"De resultaten gaan hoofdzakelijk over **{topics}**. "
        f"De links zijn afkomstig van meerdere websites (nieuws, blogs en informatiepagina's)."
    )
    return summary

# ---------- SESSION STATE ----------
if "resultaten" not in st.session_state:
    st.session_state.resultaten = []
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "num_results" not in st.session_state:
    st.session_state.num_results = 10
if "used_source" not in st.session_state:
    st.session_state.used_source = None
if "used_endpoint" not in st.session_state:
    st.session_state.used_endpoint = None
if "last_error" not in st.session_state:
    st.session_state.last_error = None

# ---------- UI ELEMENTS ----------
zoekterm = st.text_input(
    "Wat wil je zoeken?",
    placeholder="Bijv. beste restaurants Amsterdam",
    value=st.session_state.get("last_query", "")
)

tijd_filter = st.selectbox("⏰ Tijd filteren (placeholder)", ["Alles", "Afgelopen dag", "Afgelopen week", "Afgelopen maand"])

col1, col2 = st.columns([4, 1])
with col1:
    search_clicked = st.button("🔎 Zoeken", use_container_width=True)
with col2:
    more_clicked = st.button("🔄 Toon meer", use_container_width=True)

# ---------- ACTIES (zoek + fallback cascade) ----------
def run_search_with_fallback(query):
    session = make_session()
    st.session_state.last_error = None
    # 1) DuckDuckGo (multiple endpoints internally)
    try:
        res, src, ep = search_duckduckgo(query, max_results=40, session=session)
        st.session_state.used_source = src
        st.session_state.used_endpoint = ep
        return res
    except Exception as e_ddg:
        st.session_state.last_error = str(e_ddg)
        # try Brave
        try:
            res, src, ep = search_brave(query, max_results=30, session=session)
            st.session_state.used_source = src
            st.session_state.used_endpoint = ep
            return res
        except Exception as e_brave:
            st.session_state.last_error += f" || Brave: {e_brave}"
            # try Wikipedia
            try:
                res, src, ep = search_wikipedia(query, max_results=10, session=session)
                st.session_state.used_source = src
                st.session_state.used_endpoint = ep
                return res
            except Exception as e_wiki:
                st.session_state.last_error += f" || Wikipedia: {e_wiki}"
                # all failed
                return []

if search_clicked:
    if not zoekterm.strip():
        st.warning("⚠️ Voer eerst een zoekterm in!")
    elif not internet_beschikbaar():
        st.warning("📡 Geen internetverbinding.")
    else:
        with st.spinner("Zoeken (met fallback)..."):
            results = run_search_with_fallback(zoekterm.strip())
            if results:
                st.session_state.resultaten = results
                st.session_state.last_query = zoekterm.strip()
                st.session_state.num_results = 10
            else:
                st.session_state.resultaten = []
                st.error("Helaas: geen resultaten gevonden via DuckDuckGo, Brave of Wikipedia.")
                if st.session_state.last_error:
                    st.caption(f"Foutdetails: {st.session_state.last_error}")

if more_clicked:
    if st.session_state.resultaten:
        st.session_state.num_results = min(st.session_state.num_results + 10, len(st.session_state.resultaten))
    else:
        st.warning("🔎 Zoek eerst iets voordat je meer resultaten opvraagt.")

# ---------- WEERGAVE RESULTATEN ----------
resultaten = st.session_state.resultaten[:st.session_state.num_results]
totaal = len(st.session_state.resultaten)

if resultaten:
    # zichtbare info over bron
    st.success(f"✅ {len(resultaten)} resultaten getoond van {totaal} — bron: {st.session_state.used_source or 'onbekend'}")
    if st.session_state.used_endpoint:
        st.info(f"Gebruikte endpoint: {st.session_state.used_endpoint}")
    st.progress(len(resultaten)/totaal if totaal > 0 else 0)

    st.markdown("### 🌐 Zoekresultaten")
    st.divider()
    for i, r in enumerate(resultaten, 1):
        favicon_html = f"<img src='{r['favicon']}' style='width:16px;height:16px;margin-right:6px;vertical-align:middle;'>" if r.get("favicon") else ""
        suspicious_label = " ⚠️" if r.get("suspicious") else ""
        st.markdown(f"{favicon_html} **{i}. [{r['title']}]({r['url']})**{suspicious_label}", unsafe_allow_html=True)

    st.divider()
    st.markdown("🧠 **Lokale AI-samenvatting**")
    st.info(generate_local_summary(resultaten))

else:
    st.info("Voer een zoekterm in en klik op 🔎 Zoeken om resultaten te zien.")
    if st.session_state.last_error:
        st.caption(f"Laatste fout (voor debugging): {st.session_state.last_error}")

st.caption("💡 Tip: Als fallback steeds faalt kan dat aan netwerk- of host-blokkades liggen (bv. Streamlit Cloud). Probeer lokaal op je machine of test met andere netwerken.")