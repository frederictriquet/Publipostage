#!/usr/bin/env python3
"""Obtient un access token YouTube via OAuth 2.0."""

import os
import sys

CLIENT_SECRETS_FILE = os.environ.get(
    "YOUTUBE_CLIENT_SECRETS_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "youtube_client_secrets.json"),
)
TOKEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "youtube_token.json")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not os.path.isfile(CLIENT_SECRETS_FILE):
        print(f"Erreur : fichier de secrets introuvable : {CLIENT_SECRETS_FILE}")
        print("Télécharge client_secrets.json depuis Google Cloud Console")
        print("et place-le ici, ou définis YOUTUBE_CLIENT_SECRETS_FILE.")
        sys.exit(1)

    print("Ouverture du navigateur pour l'autorisation YouTube...")
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    print(f"Token sauvegardé : {TOKEN_PATH}")


if __name__ == "__main__":
    main()
