# Publipostage

CLI pour publier des vidéos sur Instagram (TikTok a venir).

## Installation

```bash
uv venv && uv pip install -r requirements.txt
```

## Configuration

Variables d'environnement (via `.envrc` / direnv) :

```bash
export INSTAGRAM_ACCOUNT_ID="..."
export INSTAGRAM_ACCESS_TOKEN="..."
```

## Usage

```bash
# Couverture par timestamp
python publipostage.py --video clip.mp4 --texte caption.txt --thumbnail-at 5

# Couverture par image
python publipostage.py --video clip.mp4 --texte caption.txt --thumbnail cover.jpg

# Sans couverture custom
python publipostage.py --video clip.mp4 --texte caption.txt
```
