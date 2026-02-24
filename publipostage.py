#!/usr/bin/env python3
"""Publipostage - Publie des vidéos sur Instagram depuis la ligne de commande."""

import argparse
import os
import sys
import time

import requests

API_BASE = "https://graph.instagram.com/v25.0"
TEMP_HOST = "https://tmpfiles.org/api/v1/upload"


def read_caption(path):
    """Lit le texte de caption depuis un fichier."""
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def timestamp_to_ms(ts):
    """Convertit un timestamp en millisecondes.

    Formats acceptés : "5", "5.5", "0:05", "00:00:05"
    """
    if ":" in ts:
        parts = ts.split(":")
        if len(parts) == 3:
            h, m, s = parts
            seconds = int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            seconds = int(m) * 60 + float(s)
        else:
            raise ValueError(f"Format de timestamp invalide : {ts}")
    else:
        seconds = float(ts)
    return int(seconds * 1000)


def upload_temp(file_path):
    """Upload un fichier sur un hébergement temporaire, retourne l'URL publique."""
    file_size = os.path.getsize(file_path) / (1024 * 1024)
    if file_size > 512:
        print(f"Erreur : fichier trop volumineux ({file_size:.0f} Mo, max 512 Mo)", file=sys.stderr)
        sys.exit(1)

    with open(file_path, "rb") as f:
        resp = requests.post(
            TEMP_HOST,
            files={"file": (os.path.basename(file_path), f)},
            timeout=600,
        )
    resp.raise_for_status()
    data = resp.json()
    # tmpfiles.org retourne une URL de page, il faut insérer /dl/ pour le lien direct
    url = data["data"]["url"]
    return url.replace("tmpfiles.org/", "tmpfiles.org/dl/")


def create_container(account_id, token, video_url, caption, thumb_offset=None, cover_url=None):
    """Crée un container média Instagram."""
    data = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": token,
    }
    if thumb_offset is not None:
        data["thumb_offset"] = thumb_offset
    if cover_url:
        data["cover_url"] = cover_url

    resp = requests.post(f"{API_BASE}/{account_id}/media", data=data, timeout=30)
    if not resp.ok:
        print(f"Erreur API : {resp.status_code} {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    return resp.json()["id"]


def wait_for_ready(container_id, token, timeout=300, interval=5):
    """Attend que le container soit prêt pour la publication."""
    elapsed = 0
    while elapsed < timeout:
        resp = requests.get(
            f"{API_BASE}/{container_id}",
            params={"fields": "status_code,status", "access_token": token},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status_code")

        if status == "FINISHED":
            return True
        if status == "ERROR":
            print(f"Erreur de traitement : {data.get('status')}", file=sys.stderr)
            return False

        print(f"  Traitement en cours ({status})...")
        time.sleep(interval)
        elapsed += interval

    print("Timeout : traitement trop long", file=sys.stderr)
    return False


def publish_media(account_id, container_id, token):
    """Publie le média traité."""
    resp = requests.post(
        f"{API_BASE}/{account_id}/media_publish",
        data={"creation_id": container_id, "access_token": token},
        timeout=30,
    )
    if not resp.ok:
        print(f"Erreur API : {resp.status_code} {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Publie une vidéo sur Instagram")
    parser.add_argument("--video", required=True, help="Chemin vers le fichier vidéo")
    parser.add_argument(
        "--texte", required=True, help="Chemin vers le fichier texte (caption)"
    )

    thumb = parser.add_mutually_exclusive_group()
    thumb.add_argument(
        "--thumbnail", help="Image de couverture (fichier local ou URL)"
    )
    thumb.add_argument(
        "--thumbnail-at",
        help="Timestamp pour la couverture (ex: 5, 0:05, 00:00:05)",
    )

    args = parser.parse_args()

    # Validation des fichiers
    if not os.path.isfile(args.video):
        parser.error(f"Vidéo introuvable : {args.video}")
    if not os.path.isfile(args.texte):
        parser.error(f"Fichier texte introuvable : {args.texte}")

    # Credentials
    account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not account_id or not token:
        print(
            "Erreur : INSTAGRAM_ACCOUNT_ID et INSTAGRAM_ACCESS_TOKEN requis",
            file=sys.stderr,
        )
        sys.exit(1)

    caption = read_caption(args.texte)
    print(f"Caption : {caption[:80]}{'...' if len(caption) > 80 else ''}")

    # Thumbnail
    thumb_offset = None
    cover_url = None

    if args.thumbnail_at:
        thumb_offset = timestamp_to_ms(args.thumbnail_at)
        print(f"Couverture : frame à {args.thumbnail_at}")
    elif args.thumbnail:
        if args.thumbnail.startswith(("http://", "https://")):
            cover_url = args.thumbnail
        else:
            if not os.path.isfile(args.thumbnail):
                parser.error(f"Image introuvable : {args.thumbnail}")
            print("Upload de l'image de couverture...")
            cover_url = upload_temp(args.thumbnail)
            print(f"  OK : {cover_url}")

    # Upload vidéo sur hébergement temporaire
    size_mb = os.path.getsize(args.video) / (1024 * 1024)
    print(f"Upload de la vidéo ({size_mb:.1f} Mo)...")
    video_url = upload_temp(args.video)
    print(f"  OK : {video_url}")

    # Création du container Instagram
    print("Création du container Instagram...")
    container_id = create_container(
        account_id, token, video_url, caption,
        thumb_offset=thumb_offset, cover_url=cover_url,
    )
    print(f"  Container : {container_id}")

    # Attente du traitement
    print("Traitement par Instagram...")
    if not wait_for_ready(container_id, token):
        sys.exit(1)

    # Publication
    print("Publication...")
    result = publish_media(account_id, container_id, token)
    print(f"Publié ! ID : {result.get('id')}")


if __name__ == "__main__":
    main()
