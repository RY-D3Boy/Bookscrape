"""
scraper.py — Responsabilité unique : télécharger et extraire les données brutes.
════════════════════════════════════════════════════════════════════════════════
Ce module ne transforme rien et ne sauvegarde rien.
Il retourne les données telles qu'elles apparaissent sur le site,
avec uniquement la gestion des erreurs réseau et des champs manquants.

Spécificité Bookscrape2 : deux variables de module (nb_requetes, erreurs)
accumulent les statistiques de la session. Elles sont lues par main.py
après le scraping pour afficher le récapitulatif final.

Flux interne :
    scrape_all_books()
        └─ get_categories()          → liste des 50 catégories + leurs URLs
        └─ scrape_category()         → parcourt toutes les pages d'une catégorie
               └─ fetch_page()       → télécharge une page (retry automatique)
               └─ get_books_from_page() → extrait les livres d'une page HTML
               └─ get_next_page_url()   → URL de la page suivante ou None
════════════════════════════════════════════════════════════════════════════════
"""

import requests
from bs4 import BeautifulSoup
import time
import logging

# URL racine du site — utilisée pour construire les URLs absolues des catégories
BASE_URL = "https://books.toscrape.com/"

# Correspondance CSS class → note numérique.
# Le site encode la note dans la classe de la balise <p> (ex: "star-rating Three").
# Si la classe est absente ou inconnue, la note vaut 0 par défaut.
RATING_MAP = {
    "One":   1,
    "Two":   2,
    "Three": 3,
    "Four":  4,
    "Five":  5,
}

MAX_RETRIES = 3   # Nombre maximum de tentatives par page avant abandon
RETRY_DELAY = 5   # Délai (en secondes) entre deux tentatives successives

# ── Statistiques de session ───────────────────────────────────────────────────
# Ces variables sont remises à zéro à chaque import du module (un import par run).
# main.py les lit via `scraper.nb_requetes` et `scraper.erreurs` après le scraping
# pour produire le récapitulatif final dans les logs.
nb_requetes = 0   # Total de requêtes HTTP envoyées (y compris les retries)
erreurs     = []  # Messages d'erreur collectés tout au long du scraping
# ─────────────────────────────────────────────────────────────────────────────


# ── Téléchargement ────────────────────────────────────────────────────────────

def fetch_page(url):
    """
    Télécharge une page web et la retourne parsée (BeautifulSoup).
    Retourne None si toutes les tentatives ont échoué.

    Mécanisme de retry :
      - MAX_RETRIES tentatives avec RETRY_DELAY secondes d'attente entre chacune.
      - Chaque tentative incrémente nb_requetes (compteur de session).
      - Gère séparément : ConnectionError, Timeout, HTTPError (4xx/5xx).
      - En cas d'échec définitif, le message est ajouté à `erreurs` et None est retourné.

    Encodage :
      - Forcé à UTF-8 car requests peut auto-détecter latin-1 sur ce site,
        ce qui provoquerait des caractères parasites dans les prix (ex: "Â£").
    """
    global nb_requetes
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            nb_requetes += 1
            response = requests.get(url, timeout=10)
            response.raise_for_status()          # Lève HTTPError si statut >= 400
            response.encoding = "utf-8"          # Force UTF-8 (évite le latin-1 auto-détecté)
            return BeautifulSoup(response.text, "html.parser")

        except requests.exceptions.ConnectionError:
            logging.warning(f"  ⚠ Connexion impossible ({url}) — tentative {attempt}/{MAX_RETRIES}")
        except requests.exceptions.Timeout:
            logging.warning(f"  ⚠ Timeout ({url}) — tentative {attempt}/{MAX_RETRIES}")
        except requests.exceptions.HTTPError as e:
            logging.warning(f"  ⚠ Erreur HTTP {e.response.status_code} ({url}) — tentative {attempt}/{MAX_RETRIES}")

        if attempt < MAX_RETRIES:
            logging.info(f"  ↻ Nouvelle tentative dans {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)

    msg = f"Page abandonnée après {MAX_RETRIES} tentatives : {url}"
    logging.error(f"  ✗ {msg}")
    erreurs.append(msg)   # Conservé pour le récapitulatif de fin de run dans main.py
    return None


# ── Extraction des catégories ─────────────────────────────────────────────────

def get_categories(soup):
    """
    Extrait la liste des catégories depuis le menu latéral de la page d'accueil.
    Retourne une liste de tuples (nom, url_absolue).

    Sélecteur CSS : "ul.nav-list > li > ul > li > a"
      - ul.