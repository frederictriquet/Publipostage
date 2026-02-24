#!/usr/bin/env python3
"""Obtient un access token TikTok via OAuth 2.0 avec PKCE."""

import base64
import hashlib
import os
import urllib.parse
import webbrowser

import requests

CLIENT_KEY = "sbaw4pdd41a3yzakcy"
CLIENT_SECRET = "09OowXvAmjuVTnDBaPsH60TqWrMkHRhm"
REDIRECT_URI = "https://frederictriquet.github.io/Publipostage/callback.html"
SCOPE = "video.publish"


def generate_pkce():
    """Génère code_verifier et code_challenge pour PKCE."""
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def main():
    code_verifier, code_challenge = generate_pkce()

    # 1. Ouvrir l'URL d'autorisation avec PKCE
    params = urllib.parse.urlencode({
        "client_key": CLIENT_KEY,
        "scope": SCOPE,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    auth_url = f"https://www.tiktok.com/v2/auth/authorize/?{params}"

    print("Ouverture du navigateur pour l'autorisation TikTok...")
    webbrowser.open(auth_url)

    # 2. L'utilisateur copie le code depuis la page callback
    print("\nApres autorisation, copie le code affiche sur la page et colle-le ici.")
    auth_code = input("Code : ").strip()

    if not auth_code:
        print("Erreur : pas de code fourni")
        return

    print("Echange contre un token...")

    # 3. Echanger le code contre un token
    resp = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": CLIENT_KEY,
            "client_secret": CLIENT_SECRET,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if "access_token" not in data:
        print(f"Erreur : {data}")
        return

    print(f"\n--- Token TikTok ---")
    print(f"Access Token  : {data['access_token']}")
    print(f"Refresh Token : {data.get('refresh_token', 'N/A')}")
    print(f"Expires in    : {data.get('expires_in', '?')}s")
    print(f"\nAjoute dans .envrc :")
    print(f'export TIKTOK_ACCESS_TOKEN="{data["access_token"]}"')


if __name__ == "__main__":
    main()
