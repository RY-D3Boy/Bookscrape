FROM python:3.9-slim

# PYTHONDONTWRITEBYTECODE : évite les fichiers .pyc dans /app/src.
# Utile car src/ est monté en volume depuis l'hôte — on ne veut pas
# que le container écrive du cache dans les sources locales.
ENV PYTHONDONTWRITEBYTECODE=1

# PYTHONUNBUFFERED : désactive le buffer de stdout/stderr.
# Les logs Python apparaissent immédiatement dans cron.log et `docker logs`,
# sans attendre que le buffer soit plein.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ── Dépendances système ───────────────────────────────────────────────────────
# On installe uniquement cron (planificateur de tâches).
# --no-install-recommends et rm -rf réduisent la taille de l'image.
RUN apt-get update && apt-get install -y --no-install-re