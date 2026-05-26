"""
checker.py — Responsabilité : comparer la structure HTML actuelle avec la référence.
════════════════════════════════════════════════════════════════════════════════
- Premier run : génère automatiquement le fichier de référence (structure.json).
- Runs suivants : compare et enregistre les écarts dans reference/changes.json.
- structure.json n'est JAMAIS modifié automatiquement lors des comparaisons.

Détections couvertes :
  1. Sélecteurs HTML cassés   → un sélecteur CSS ne retourne plus rien
  2. Écarts de volume         → nombre de catégories ou de livres/page différent
  3. Renommage de catégorie   → comparaison nom par nom via categories_list
════════════════════════════════════════════════════════════════════════════════
"""

import json
import os
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date

# En Docker, /app/src est le répertoire courant → on remonte pour reference/
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
REFERENCE_PATH = os.path.join(BASE_DIR, "..", "reference", "structure.json")
CHANGES_PATH   = os.path.join(BASE_DIR, "..", "reference", "changes.json")
SAMPLE_URL     = "https://books.toscrape.com/catalogue/page-1.html"

# Sélecteurs CSS utilisés par scraper.py pour extraire les données.
# Ils servent à la fois de référence pour le monitoring et de source
# de vérité pour savoir ce que le scraper attend du HTML.
SELECTEURS = {
    "article":    "article.product_pod",
    "titre":      "h3 > a",
    "prix":       "p.price_color",
    "note":       "p.star-rating",
    "categories": "ul.nav-list > li > ul > li > a",
}


# ── Téléchargement de la page échantillon ────────────────────────────────────

def fetch_sample_page():
    """
    Télécharge la page 1 du catalogue comme page d'échantillon pour la vérification.
    Retourne un objet BeautifulSoup ou None en cas d'erreur réseau.

    On utilise une page du catalogue (pas la page d'accueil) car elle contient
    les éléments article, titre, prix et note que l'on veut tester.
    """
    try:
        response = requests.get(SAMPLE_URL, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"
        return BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.RequestException as e:
        logging.warning(f"⚠️ Impossible de charger la page échantillon : {e}")
        return None


# ── Création et lecture de la référence ──────────────────────────────────────

def create_reference(soup):
    """
    Génère reference/structure.json au premier run.

    Contenu sauvegardé :
      - date_reference   : date de création (pour traçabilité)
      - nb_categories    : nombre de catégories présentes
      - nb_livres_page1  : nombre de livres sur la première page
      - categories_list  : liste triée des noms de catégories (pour détecter les renommages)
      - selecteurs       : sélecteurs CSS utilisés par scraper.py

    Le dossier reference/ est créé automatiquement s'il n'existe pas
    (Docker monte le volume, mais au premier run le dossier peut ne pas exister encore).
    """
    os.makedirs(os.path.dirname(REFERENCE_PATH), exist_ok=True)

    categories = sorted([link.text.strip() for link in soup.select(SELECTEURS["categories"])])

    reference = {
        "date_reference":  date.today().strftime("%d/%m/%Y"),
        "nb_categories":   len(categories),
        "nb_livres_page1": len(soup.select(SELECTEURS["article"])),
        "categories_list": categories,
        "selecteurs":      SELECTEURS,
        "note": "Généré automatiquement au premier run. Ne pas modifier automatiquement."
    }

    with open(REFERENCE_PATH, "w", encoding="utf-8") as f:
        json.dump(reference, f, ensure_ascii=False, indent=2)

    logging.info(f"📄 Référence créée : {reference['nb_categories']} catégories, {reference['nb_livres_page1']} livres/page.")


def load_reference():
    """Charge et retourne le contenu de structure.json."""
    with open(REFERENCE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Enregistrement des anomalies ──────────────────────────────────────────────

def save_change(anomalies):
    """
    Enregistre les anomalies détectées dans reference/changes.json avec horodatage.
    Crée le fichier s'il n'existe pas, sinon ajoute à l'historique existant.

    Format d'une entrée :
      { "date": "JJ/MM/AAAA HH:MM:SS", "anomalies": ["message 1", "message 2"] }
    """
    history = []

    if os.path.isfile(CHANGES_PATH):
        with open(CHANGES_PATH, "r", encoding="utf-8") as f:
            history = json.load(f)

    history.append({
        "date":      datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "anomalies":