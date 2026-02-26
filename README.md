# Publipostage

Publipostage is an open-source command-line tool designed for independent content creators and musicians who manage their own social media presence.

It allows creators to publish videos with captions to TikTok and Instagram directly from their terminal, without manual uploading. The tool is freely available on GitHub (https://github.com/frederictriquet/Publipostage) and can be used by any content creator. It uses the TikTok Content Posting API to upload videos on behalf of authenticated users via OAuth 2.0.

Use case: a creator prepares a video and a caption file, runs the CLI, and the video is published to their TikTok account. The tool never stores credentials server-side: authentication tokens are kept locally on the user's machine.

## Installation

```bash
uv venv && uv pip install -r requirements.txt
```

## Configuration

Environment variables (via `.envrc` / direnv):

```bash
# Instagram
export INSTAGRAM_ACCOUNT_ID="..."
export INSTAGRAM_ACCESS_TOKEN="..."

# TikTok
export TIKTOK_ACCESS_TOKEN="..."
```

## Usage

```bash
# Interactive mode (lists available media in configured directory)
python publipostage.py

# Publish to both platforms (default)
python publipostage.py --video clip.mp4 --texte caption.txt

# Publish to a specific platform
python publipostage.py --platform ig   # Instagram only
python publipostage.py --platform tt   # TikTok only
python publipostage.py --platform all  # Both (default)

# Cover image from video timestamp
python publipostage.py --video clip.mp4 --texte caption.txt --thumbnail-at 5

# Cover image from file
python publipostage.py --video clip.mp4 --texte caption.txt --thumbnail cover.jpg

# Dry run (no actual publishing)
python publipostage.py --dry-run
```

## TikTok authentication

Run the OAuth flow to get an access token:

```bash
python tiktok_auth.py
```

This opens a browser window, you authorize the app, and the token is displayed for you to copy into `.envrc`.
