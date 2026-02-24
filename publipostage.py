#!/usr/bin/env python3
"""Publipostage - Publie des vidéos sur Instagram depuis la ligne de commande."""

import argparse
import os
import shutil
import sys
import time
import tomllib

import requests

API_BASE = "https://graph.instagram.com/v25.0"
TEMP_HOST = "https://tmpfiles.org/api/v1/upload"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.toml")


def load_config():
    """Charge la configuration depuis config.toml."""
    if not os.path.isfile(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


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


def resolve_path(path, media_dir):
    """Résout un chemin : absolu tel quel, relatif cherché dans media_dir puis cwd."""
    if os.path.isabs(path):
        return path
    if media_dir:
        candidate = os.path.join(media_dir, path)
        if os.path.exists(candidate):
            return candidate
    return path


def list_available_media(media_dir):
    """Liste les médias publiables (paires .mp4 + .txt) dans media_dir."""
    if not os.path.isdir(media_dir):
        print(f"Erreur : répertoire introuvable : {media_dir}", file=sys.stderr)
        sys.exit(1)

    videos = {os.path.splitext(f)[0] for f in os.listdir(media_dir) if f.endswith(".mp4")}
    texts = {os.path.splitext(f)[0] for f in os.listdir(media_dir) if f.endswith(".txt")}
    available = sorted(videos & texts)

    if not available:
        print(f"Aucun média publiable dans {media_dir}", file=sys.stderr)
        print("(il faut un .mp4 ET un .txt avec le même nom)", file=sys.stderr)
        sys.exit(1)

    return available


def prompt_media_choice(available):
    """Affiche la liste et demande à l'utilisateur de choisir."""
    print("Médias disponibles :\n")
    for i, name in enumerate(available, 1):
        print(f"  {i}. {name}")
    print()

    while True:
        try:
            choice = input("Choix (numéro) : ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(available):
                return available[idx]
        except (ValueError, EOFError):
            pass
        print(f"Choix invalide, entre 1 et {len(available)}")


def main():
    config = load_config()
    defaults = config.get("defaults", {})
    media_dir = defaults.get("media_dir")

    parser = argparse.ArgumentParser(description="Publie une vidéo sur Instagram")
    parser.add_argument("--video", help="Chemin vers le fichier vidéo")
    parser.add_argument("--texte", help="Chemin vers le fichier texte (caption)")

    thumb = parser.add_mutually_exclusive_group()
    thumb.add_argument(
        "--thumbnail", help="Image de couverture (fichier local ou URL)"
    )
    thumb.add_argument(
        "--thumbnail-at",
        default=defaults.get("thumbnail_at"),
        help="Timestamp pour la couverture (ex: 5, 0:05, 00:00:05)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simule la publication sans poster sur Instagram",
    )

    args = parser.parse_args()

    # Mode interactif si --video et --texte ne sont pas fournis
    if not args.video and not args.texte:
        if not media_dir:
            parser.error("--video et --texte requis (ou configurer media_dir dans config.toml)")
        chosen = prompt_media_choice(list_available_media(media_dir))
        args.video = os.path.join(media_dir, f"{chosen}.mp4")
        args.texte = os.path.join(media_dir, f"{chosen}.txt")
    elif not args.video or not args.texte:
        parser.error("--video et --texte doivent être fournis ensemble")

    # Résolution des chemins via media_dir
    args.video = resolve_path(args.video, media_dir)
    args.texte = resolve_path(args.texte, media_dir)
    if args.thumbnail and not args.thumbnail.startswith(("http://", "https://")):
        args.thumbnail = resolve_path(args.thumbnail, media_dir)

    # Validation des fichiers
    if not os.path.isfile(args.video):
        parser.error(f"Vidéo introuvable : {args.video}")
    if not os.path.isfile(args.texte):
        parser.error(f"Fichier texte introuvable : {args.texte}")

    # Credentials (pas requis en dry-run)
    account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not args.dry_run and (not account_id or not token):
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

    if args.dry_run:
        size_mb = os.path.getsize(args.video) / (1024 * 1024)
        print(f"\n[DRY RUN] Résumé :")
        print(f"  Vidéo    : {args.video} ({size_mb:.1f} Mo)")
        print(f"  Caption  : {caption[:80]}{'...' if len(caption) > 80 else ''}")
        if thumb_offset is not None:
            print(f"  Thumbnail: frame à {thumb_offset}ms")
        elif cover_url:
            print(f"  Thumbnail: {cover_url}")
        print(f"\nAucune publication effectuée.")
        return

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

    # Déplacement vers le répertoire Published
    published_dir = defaults.get("published_dir")
    if published_dir:
        os.makedirs(published_dir, exist_ok=True)
        for path in (args.video, args.texte):
            dest = os.path.join(published_dir, os.path.basename(path))
            shutil.move(path, dest)
            print(f"  Déplacé : {os.path.basename(path)} -> Published/")


if __name__ == "__main__":
    main()
