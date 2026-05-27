# 📚 Bookscrape

Pipeline ETL automatisée et containerisée pour extraire, transformer et sauvegarder les données du site [books.toscrape.com](https://books.toscrape.com).

> Version 2 du projet — intègre Docker, planification cron automatique et suivi des statistiques de requêtes.

---

## 🧭 Vue d'ensemble

```
[books.toscrape.com] ──► Scraping ──► Transformation ──► Sauvegarde CSV
                                            │
                                    Monitoring HTML (checker)
                                            │
                                   [cron — 1x par mois]
                                   [Docker container]
```

À chaque exécution (automatique ou manuelle) :
1. **Vérifie** la structure HTML du site (avant de scrapper)
2. **Scrappe** tous les livres du site (toutes catégories, toutes pages)
3. **Nettoie** les données (prix, date)
4. **Sauvegarde** dans `DATA/books.csv` en mode append
5. **Affiche** un récapitulatif : nombre de requêtes HTTP et erreurs éventuelles

---

## 🗂️ Structure du projet

```
Bookscrape2/
├── src/
│   ├── main.py        # Point d'entrée — orchestre la pipeline
│   ├── scraper.py     # Étape 1 : téléchargement et extraction brute
│   ├── transform.py   # Étape 2 : nettoyage et enrichissement
│   └── checker.py     # Monitoring de la structure HTML du site
├── DATA/
│   └── books.csv      # Données extraites (généré à l'exécution)
├── logs/
│   ├── scraper.log    # Logs détaillés de la pipeline Python
│   └── cron.log       # Résumé de chaque run (capturé par cron)
├── reference/
│   ├── structure.json # Référence HTML générée au 1er run
│   └── changes.json   # Historique des anomalies détectées
├── Dockerfile         # Image Docker : Python 3.9 + cron
├── docker-compose.yml # Orchestration des volumes et du container
├── crontab.sh         # Planification : 1er de chaque mois à 10h00
├── entrypoint.sh      # Script de démarrage du container
└── requirements.txt   # Dépendances Python
```

---

## ⚙️ Prérequis

- **Docker** et **Docker Compose** installés
- Pour un lancement manuel sans Docker : Python 3.8+ + `pip install -r requirements.txt`

---

## 🚀 Démarrage avec Docker

### 1. Cloner le dépôt

```bash
git clone https://github.com/RY-D3Boy/Bookscrape.git
cd Bookscrape
```

### 2. Lancer le container

```bash
docker-compose up -d --build
```

Le container démarre et attend le prochain déclenchement cron.

### 3. Vérifier que le container tourne

```bash
docker ps
# → bookscrape_scheduler   Up X minutes
```

### 4. Suivre les logs en temps réel

```bash
docker logs -f bookscrape_scheduler
```

---

## ⏰ Planification automatique

La pipeline tourne automatiquement **le 1er de chaque mois à 10h00** (heure du container).

Définie dans `crontab.sh` :
```
0 10 1 * *  cd /app/src && python main.py 2>&1 | tee -a /app/logs/cron.log > /proc/1/fd/1
```

Le résumé de chaque run (nombre de livres, durée) est visible dans `logs/cron.log`.

---

## ▶️ Lancement manuel

### Dans le container en cours d'exécution

```bash
docker exec bookscrape_scheduler python /app/src/main.py
```

### Sans Docker (développement local)

```bash
cd src
python main.py
```

---

## 📁 Fichier de sortie

Les données sont sauvegardées dans `DATA/books.csv` :

| Colonne | Description | Exemple |
|---|---|---|
| `Catégorie` | Catégorie du livre | `Mystery` |
| `Titre` | Titre complet du livre | `Sharp Objects` |
| `Prix` | Prix en livres sterling | `47.82` |
| `Note (étoiles)` | Note de 1 à 5 | `4` |
| `Date d'ajout` | Date du scraping (JJ/MM/AAAA) | `26/05/2026` |

**Format** : CSV avec séparateur `;`, encodage UTF-8 avec BOM (compatible Excel).
**Mode** : append — chaque run ajoute des lignes sans écraser les précédentes.

---

## 📊 Récapitulatif de fin de run

À la fin de chaque exécution, les logs affichent :

```
── RÉCAPITULATIF ──
  Requêtes HTTP envoyées : 312
  Aucune erreur constatée
══════════════════════════════════════════
✅ Pipeline terminée — 1000 livres sauvegardés | Durée : 0:02:41
```

En cas d'erreurs :
```
── RÉCAPITULATIF ──
  Requêtes HTTP envoyées : 298
  3 erreur(s) constatée(s) :
    • Page abandonnée après 3 tentatives : https://...
    • Titre manquant dans la catégorie 'Mystery'
    • Prix manquant pour 'Sharp Objects'
```

---

## 🔍 Monitoring HTML (`checker.py`)

### Premier run

Génère automatiquement `reference/structure.json` avec :
- les sélecteurs CSS utilisés
- le nombre de catégories et de livres/page
- la liste complète des noms de catégories

### Runs suivants — 3 niveaux de vérification

1. **Sélecteurs CSS** — les balises HTML sont-elles toujours présentes ?
2. **Volumes** — le nombre de catégories et de livres correspond-il à la référence ?
3. **Noms de catégories** — chaque catégorie a-t-elle le même nom ? (détecte les renommages)

Toute anomalie est loggée en WARNING et enregistrée dans `reference/changes.json`.

### Migration automatique

Si un `structure.json` existant ne contient pas encore `categories_list` (ancienne version), il est mis à jour automatiquement au prochain run.

---

## ⚠️ Messages d'alerte — référence complète

### Réseau

| Message | Niveau | Cause | Action |
|---|---|---|---|
| `⚠ Connexion impossible (url) — tentative X/3` | WARNING | Serveur inaccessible | Retry automatique (5s de délai) |
| `⚠ Timeout (url) — tentative X/3` | WARNING | Réponse > 10s | Retry automatique |
| `⚠ Erreur HTTP 4xx/5xx (url) — tentative X/3` | WARNING | Erreur serveur | Retry automatique |
| `✗ Page abandonnée après 3 tentatives` | ERROR | 3 échecs consécutifs | Page ignorée, pipeline continue |
| `✗ Catégorie 'X' interrompue à la page N` | ERROR | Page de catégorie inaccessible | Catégorie abandonnée, pipeline continue |
| `✗ Impossible d'accéder à la page d'accueil` | ERROR | Site totalement inaccessible | Scraping annulé, CSV non modifié |
| `⚠️ Impossible de charger la page échantillon` | WARNING | Checker ne peut pas fetch | Vérification ignorée, scraping continue |

### Données manquantes

| Message | Niveau | Cause | Action |
|---|---|---|---|
| `⚠ Titre manquant dans la catégorie 'X'` | WARNING | Balise `h3 > a` absente | Valeur "Titre inconnu", ajout dans erreurs[] |
| `⚠ Prix manquant pour 'Titre'` | WARNING | Balise `p.price_color` absente | Prix vide, ajout dans erreurs[] |
| `⚠ Note manquante pour 'Titre'` | WARNING | Balise `p.star-rating` absente | Note = 0, ajout dans erreurs[] |

### Monitoring HTML

| Message | Niveau | Cause | Action |
|---|---|---|---|
| `⚠️ BALISES HTML MODIFIÉES PAR RAPPORT À LA RÉFÉRENCE` | WARNING | Sélecteur CSS cassé | Mettre à jour les sélecteurs dans `scraper.py` |
| `⚠️ CHANGEMENTS DE CATÉGORIES DÉTECTÉS` | WARNING | Noms de catégories modifiés | Vérifier renommage / ajout / suppression |
| `• Catégorie absente (disparue ou renommée) : 'X'` | WARNING | 'X' absent du site | Voir si elle a été renommée |
| `• Nouvelle catégorie détectée : 'X'` | WARNING | 'X' absent de la référence | Voir si elle remplace une catégorie disparue |
| `→ Probable renommage` | WARNING | Disparition + apparition simultanée | Mettre à jour la référence si besoin |
| `⚠️ ÉCARTS DE VOLUME DÉTECTÉS` | WARNING | Nombre de catégories ou livres/page différent | Vérifier le site manuellement |

### Sauvegarde

| Message | Niveau | Cause | Action |
|---|---|---|---|
| `✗ Impossible d'écrire 'filepath'` | ERROR | Fichier CSV verrouillé | Vérifier les permissions Docker (volume mal monté) |
| `✗ Aucun livre récupéré. Pipeline arrêtée.` | ERROR | `scrape_all_books()` a retourné `[]` | Vérifier le réseau et relancer |

---

## 🐳 Architecture Docker

| Composant | Rôle |
|---|---|
| `Dockerfile` | Image Python 3.9 slim avec cron installé |
| `docker-compose.yml` | Monte les volumes locaux dans `/app/`, configure `restart: unless-stopped` |
| `crontab.sh` | Définit le déclenchement mensuel (1er du mois, 10h00) |
| `entrypoint.sh` | Lance `cron -f` en foreground (PID 1) pour maintenir le container actif |

### Volumes montés

| Local | Dans le container | Contenu |
|---|---|---|
| `./src` | `/app/src` | Code Python (modifiable à chaud) |
| `./DATA` | `/app/data` | Fichier CSV de sortie |
| `./logs` | `/app/logs` | scraper.log + cron.log |
| `./reference` | `/app/reference` | structure.json + changes.json |

### Commandes utiles

```bash
# Démarrer
docker-compose up -d --build

# Arrêter
docker-compose down

# Voir les logs en temps réel
docker logs -f bookscrape_scheduler

# Lancer un scraping immédiat
docker exec bookscrape_scheduler python /app/src/main.py

# Reconstruire l'image après modification du Dockerfile
docker-compose up -d --build --force-recreate
```

---

## 🔧 Configuration

| Fichier | Variable | Valeur | Rôle |
|---|---|---|---|
| `src/scraper.py` | `MAX_RETRIES` | `3` | Tentatives avant abandon d'une page |
| `src/scraper.py` | `RETRY_DELAY` | `5s` | Délai entre deux tentatives |
| `src/scraper.py` | `BASE_URL` | `https://books.toscrape.com/` | URL du site cible |
| `crontab.sh` | expression cron | `0 10 1 * *` | Fréquence d'exécution |

---

## 📦 Dépendances

| Package | Version | Rôle |
|---|---|---|
| `requests` | 2.31.0 | Téléchargement des pages web |
| `beautifulsoup4` | 4.12.3 | Parsing du HTML |

---

## 📄 Licence

Ce projet est open source. Le site [books.toscrape.com](https://books.toscrape.com) est un site de démonstration public, librement scrappable à des fins d'apprentissage.
