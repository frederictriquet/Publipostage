#!/usr/bin/env python3
"""Gestion automatique du token Instagram (refresh silencieux, saisie manuelle si révoqué)."""

import json
import os
from datetime import datetime, timedelta

import requests

TOKEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instagram_token.json")
INSTAGRAM_REFRESH_URL = "https://graph.instagram.com/refresh_access_token"
REFRESH_THRESHOLD_DAYS = 7


def _load_token():
    """Charge le token depuis instagram_token.json, ou None si absent."""
    if not os.path.exists(TOKEN_PATH):
        return None
    with open(TOKEN_PATH) as f:
        return json.load(f)


def _save_token(access_token, expires_at):
    """Persiste le token et sa date d'expiration."""
    with open(TOKEN_PATH, "w") as f:
        json.dump({"access_token": access_token, "expires_at": expires_at.isoformat()}, f, indent=2)


def _refresh_token(token):
    """Renouvelle le token via l'endpoint Instagram (aucune auth requise, juste le token)."""
    print("  Renouvellement du token Instagram...")  # noqa: T201
    resp = requests.get(
        INSTAGRAM_REFRESH_URL,
        params={"grant_type": "ig_refresh_token", "access_token": token},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Échec du refresh Instagram : {resp.status_code} {resp.text}")
    data = resp.json()
    expires_at = datetime.now() + timedelta(seconds=data.get("expires_in", 5184000))  # noqa: DTZ005
    _save_token(data["access_token"], expires_at)
    print(f"  Token renouvelé (expire le {expires_at.strftime('%Y-%m-%d')}).")  # noqa: T201
    return data["access_token"]


def _prompt_new_token():
    """Demande à l'utilisateur de coller un nouveau token long-lived Instagram."""
    print()  # noqa: T201
    print("  Token Instagram manquant ou révoqué.")  # noqa: T201
    print("  Pour obtenir un nouveau token long-lived (60 jours) :")  # noqa: T201
    print("  1. Va sur https://developers.facebook.com/tools/explorer")  # noqa: T201
    print("  2. Sélectionne l'app 'publipostage', génère un token avec")  # noqa: T201
    print("     les permissions : instagram_business_basic, instagram_business_content_publish")  # noqa: T201
    print("  3. Copie le token généré")  # noqa: T201
    print()  # noqa: T201
    token = input("  Colle le token ici : ").strip()
    if not token:
        raise RuntimeError("Aucun token fourni.")
    # Tente un refresh immédiat pour vérifier le token et obtenir la vraie date d'expiration
    try:
        return _refresh_token(token)
    except RuntimeError:
        # Token court (1h) ou non-refreshable : on sauvegarde tel quel avec expiry estimée
        expires_at = datetime.now() + timedelta(days=60)  # noqa: DTZ005
        _save_token(token, expires_at)
        print(f"  Token sauvegardé (expire estimé le {expires_at.strftime('%Y-%m-%d')}).")  # noqa: T201
        return token


def get_instagram_token() -> str:
    """Retourne un token Instagram valide. Refresh automatique si < 7 jours restants."""
    token_data = _load_token()

    if token_data:
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        remaining = expires_at - datetime.now()  # noqa: DTZ005

        if remaining.days > REFRESH_THRESHOLD_DAYS:
            return token_data["access_token"]

        if remaining.total_seconds() > 0:
            return _refresh_token(token_data["access_token"])

        print("  Token Instagram expiré.")  # noqa: T201

    return _prompt_new_token()


if __name__ == "__main__":
    token = get_instagram_token()
    token_data = _load_token()
    if token_data:
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        remaining = expires_at - datetime.now()  # noqa: DTZ005
        print(f"\nToken actif : {token[:20]}...")  # noqa: T201
        print(f"Expire le : {expires_at.strftime('%Y-%m-%d')} ({remaining.days} jours restants)")  # noqa: T201
