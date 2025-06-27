# app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
from bs4 import BeautifulSoup

# Flask uygulamasını başlat
app = Flask(__name__)
# Frontend'den gelen isteklere izin ver (CORS)
CORS(app)

# --- doaj_auditor.py dosyasındaki sınıfımızı buraya kopyalıyoruz ---
class DOAJAuditor:
    """
    Bir dergi web sitesini temel DOAJ kriterlerine göre analiz eden bir sınıf.
    """
    def __init__(self, journal_url):
        self.url = journal_url
        self.soup = None
        self.text_content = ""
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            self.soup = BeautifulSoup(response.content, 'html.parser')
            self.text_content = self.soup.get_text().lower()
        except requests.exceptions.RequestException as e:
            self.soup = None
            print(f"Hata: Web sitesine erişilemedi. {e}")

    def check_issn(self):
        if not self.text_content: return False
        pattern = re.compile(r'issn\s*:?\s*\d{4}-\d{3}[\dxX]', re.IGNORECASE)
        return bool(pattern.search(self.text_content))

    def check_keywords_in_links_or_text(self, keywords):
        if not self.soup: return False
        for link in self.soup.find_all('a'):
            if link.string and any(keyword.lower() in link.string.lower() for keyword in keywords):
                return True
        return any(keyword.lower()in self.text_content for keyword in keywords)

    def run_audit(self):
        if not self.soup: return {"error": "Web sitesi içeriği yüklenemedi."}
        return {
            "issn_found": self.check_issn(),
            "aims_and_scope": self.check_keywords_in_links_or_text(["amaç ve kapsam", "aims and scope"]),
            "editorial_board": self.check_keywords_in_links_or_text(["yayın kurulu", "editorial board", "editörler"]),
            "peer_review_policy": self.check_keywords_in_links_or_text(["hakemlik süreci", "peer review process", "değerlendirme süreci"]),
            "open_access_statement": self.check_keywords_in_links_or_text(["açık erişim", "open access", "creative commons", "cc by"]),
            "author_guidelines": self.check_keywords_in_links_or_text(["yazar rehberi", "author guidelines", "yazarlar için"])
        }

# --- API Endpoint (Garsonun sipariş getireceği URL) ---
@app.route('/analyze', methods=['POST'])
def analyze_journal():
    data = request.get_json()
    if not data or 'journal_url' not in data:
        return jsonify({'error': 'Dergi URL bilgisi eksik.'}), 400

    url = data['journal_url']
    auditor = DOAJAuditor(url)
    results = auditor.run_audit()

    return jsonify(results)

# Sunucuyu çalıştırmak için
if __name__ == '__main__':
    app.run(debug=True, port=5000)