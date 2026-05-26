"""
transform.py — Responsabilité unique : nettoyer et enrichir les données brutes.
════════════════════════════════════════════════════════════════════════════════
Reçoit la liste brute produite par scraper.py et retourne une liste propre,
prête à être écrite dans le CSV.

Transformations appliquées :
  1. Nettoyage du prix  → clean_price() : supprime les caractères parasites
  2. Ajout de la date   → add_date()    : date du scraping au format JJ/MM/AAAA

Ce module ne fait aucune requête réseau et ne touche pas aux fichiers.
Il est pur et facilement testable de façon isolée.
════════════════════════════════════════════════════