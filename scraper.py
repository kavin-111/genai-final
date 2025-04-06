import requests
from bs4 import BeautifulSoup

relevant_links = ["home", "about", "contact", 'services', 'products', 'company', 'investors', 'global', 'about-us']

def get_relevant_links(base_url):
    """Extract relevant page links from the homepage."""
    try:
        response = requests.get(base_url, timeout=10)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if any(keyword in href for keyword in relevant_links):
                full_url = requests.compat.urljoin(base_url, href)
                links.append(full_url)
        return list(set(links))  # Remove duplicates
    except Exception:
        return []

def scrape_text(urls):
    """Scrape and clean text from a list of URLs."""
    combined_text = ""
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                continue
            
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "header", "footer", "nav"]):
                tag.extract()
            combined_text += " ".join(soup.stripped_strings)[:2000] + " "
        except Exception:
            continue
    return combined_text
