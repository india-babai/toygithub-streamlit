# 📁 ToyGitHub

**Your private code shelf** — a lightweight [Streamlit](https://streamlit.io) app for storing, browsing, and sharing code files, backed entirely by a GitHub repository. Upload files or paste snippets from any machine, then view them anywhere with syntax highlighting — no GitHub account required on the viewing end.

It also doubles as a live GitHub repository explorer: paste any public repo URL and browse its full folder tree, view files, or download the whole repo as a ZIP.

## ✨ Features

- **🔍 Browse Files** — search stored files by name, filter by tags, and view them grouped by folder with syntax highlighting for 25+ languages (Markdown files render as formatted text).
- **🐙 GitHub Repos** — paste any public GitHub URL to browse its complete folder and file structure live, view any file, refresh to pick up new commits, and download the entire repo as a ZIP archive. Added repos are saved for future visits.
- **⬆️ Upload Files** — drag and drop multiple text/code files at once into organised folders, with optional tags and descriptions. Binary files are detected and skipped automatically.
- **📋 Paste Code** — save a snippet directly from the clipboard: name it, pick a folder, add metadata, and preview before saving.
- **🗂️ Manage Files** — edit tags and descriptions, or delete files (with confirmation).
- **📊 Dashboard** — landing page with live stats: files stored, saved repos, folders, and unique tags.

## 🏗️ How it works

There is no database. All persistence goes through the GitHub API (via [PyGithub](https://github.com/PyGithub/PyGithub)) into a single storage repository that you designate:

```
<storage repo>
├── _index.json     # metadata index: owner, folder, tags, description, upload date, blob SHA
├── _repos.json     # list of saved external GitHub repos
└── files/
    └── shared/
        └── <folder>/<filename>   # actual file contents, one commit per change
```

- `app.py` — the Streamlit UI: navigation, pages, and rendering.
- `github_storage.py` — the `GitHubStorage` class wrapping all GitHub API operations (file CRUD, metadata index, saved-repo list, external repo access).

Every upload, edit, and delete is a commit in the storage repo, so you get full version history for free.

## 🚀 Getting started

### Prerequisites

- Python 3.11+
- A GitHub [personal access token](https://github.com/settings/tokens) with read/write access to the storage repository
- A GitHub repository (private recommended) to act as the storage backend

### Installation

```bash
git clone https://github.com/india-babai/toygithub-streamlit.git
cd toygithub-streamlit

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

Create `.streamlit/secrets.toml` (already git-ignored):

```toml
github_pat   = "ghp_your_personal_access_token"
storage_repo = "your-username/your-storage-repo"
```

| Secret | Description |
|---|---|
| `github_pat` | Personal access token used for all GitHub API calls |
| `storage_repo` | `owner/name` of the repository used as the storage backend |

### Run

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

### Dev Container / Codespaces

The repo ships with a [dev container](.devcontainer/devcontainer.json) (Python 3.11): open it in GitHub Codespaces or VS Code with the Dev Containers extension, and dependencies install and the app launches automatically on port 8501.

## ☁️ Deployment

Deploys directly to [Streamlit Community Cloud](https://streamlit.io/cloud):

1. Fork or push this repo to your GitHub account.
2. Create a new Streamlit Cloud app pointing at `app.py`.
3. Add `github_pat` and `storage_repo` in the app's **Settings → Secrets**.

## ⚙️ Configuration notes

- Upload size is capped at **10 MB** per file (`.streamlit/config.toml`).
- Supported upload types include `py`, `js`, `ts`, `sql`, `yaml`, `json`, `toml`, `md`, `sh`, `go`, `rs`, `java`, `c`, `cpp`, `html`, `css`, and more — see `ALLOWED_EXTENSIONS` in `app.py`.
- All files are stored under a single shared namespace; the app is fully open by design (no accounts or auth). Deploy it behind your own access controls if you need privacy.

## 📄 License

No license file is currently included. All rights reserved by the repository owner unless a license is added.
