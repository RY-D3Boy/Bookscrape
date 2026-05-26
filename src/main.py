"""
main.py — Point d'entrée unique du projet.
══════════════════════════════════════════════════════
Lancement manuel  : python src/main.py
Lancement auto    : via cron dans le container Docker (voir crontab.sh)

Ce fichier orchestre les 3 étapes de la pipeline dans l'ordre :
    1. Scraping  → scraper.py   : télécharge les données brutes du site
    2. Transform → transform.py : nettoie et enrichit les données
    3. Save      → ce fichier   : sauvegarde dans DATA/books.csv

Deux vérifications encadrent le scraping :
    - Avant  : check_selecteurs() détecte si les balises HTML ont changé
    - Après  : check() compare les volumes obtenus avec la référence

En fin de run, un récapitulatif affiche le nombre de requêtes HTTP
et toutes les erreurs collectées via scraper.nb_requetes et scraper.erreurs.

Note Docker : le StreamHandler (console) est absent volontairement.
En container, stdout est déjà capturé par cron → logs/cron.log.
Les logs détaillés restent dans logs/scraper.log.
══════════════════════════════════════════════════════
"""

import csv
import os
import logging
from datetime import datetime

# Import du module scraper pour accéder aux compteurs de session
# (scraper.nb_requetes et scraper.erreurs) après le scraping.
import scraper
from scraper import scrape_all_books
from transform import transform
from checker import check, check_selecteurs

# ── Chemins ──────────────────────────────────────────────────────────────────
# BASE_DIR pointe sur src/, on remonte d'un niveau pour DATA/ et logs/
# En Docker, /app/src est monté depuis ./src (voir docker-compose.yml)
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(BASE_DIR, "..", "data", "books.csv")
LOG_PATH    = os.path.join(BASE_DIR, "..", "logs", "scraper.log")

# Colonnes du CSV — doit correspondre exactement aux clés produites par transform.py
FIELDNAMES = ["Catégorie", "Titre", "Prix", "Note (étoiles)", "Date d'ajout"]


# ── Configuration du logging ──────────────────────────────────────────────────

def setup_logging():
    """
    Configure la sortie de log vers le fichier logs/scraper.log uniquement.

    Le StreamHandler (terminal) a été retiré : en contexte Docker+cron,
    stdout est déjà redirigé vers logs/cron.log par la commande tee dans
    crontab.sh. Avoir deux flux dupliqués alourdirait les logs inutilement.

    Le dossier logs/ est créé automatiquement s'il n'existe pas
    (utile avant que Docker monte le volume au premier lancement).
    """
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
        ]
    )


# ── Sauvegarde CSV ────────────────────────────────────────────────────────────

def save_to_csv(books, filepath):
    """
    Sauvegarde la liste de livres dans un fichier CSV en mode append.

    Comportement :
      - Fichier absent → création avec en-tête (mode "w")
      - Fichier présent → ajout des lignes sans réécrire l'en-tête (mode "a")

    Format :
      - Séparateur  : point-virgule (;) pour compatibilité Excel français
      - Encodage    : UTF-8 avec BOM (utf-8-sig) pour ouverture correcte dans Excel
      - newline=""  : laisse DictWriter gérer les fins de ligne (évite les doubles \r\n)

    Lève PermissionError si le fichier est verrouillé.
    En Docker ce cas ne devrait pas survenir (pas d