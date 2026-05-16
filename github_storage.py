import json
from datetime import datetime, timezone

from github import Github, GithubException

INDEX_PATH = "_index.json"
REPOS_PATH = "_repos.json"
FILES_PREFIX = "files/"
SHARED_USER = "shared"


class GitHubStorage:
    def __init__(self, token: str, repo_name: str):
        self._gh = Github(token)
        self._repo = self._gh.get_repo(repo_name)

    # ------------------------------------------------------------------
    # Low-level JSON helpers
    # ------------------------------------------------------------------

    def _get_json(self, path: str, default: dict) -> dict:
        try:
            content = self._repo.get_contents(path)
            return json.loads(content.decoded_content.decode("utf-8"))
        except GithubException as e:
            if e.status == 404:
                return default
            raise

    def _put_json(self, path: str, data: dict):
        raw = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        try:
            existing = self._repo.get_contents(path)
            self._repo.update_file(path, f"Update {path}", raw, existing.sha)
        except GithubException as e:
            if e.status == 404:
                self._repo.create_file(path, f"Create {path}", raw)
            else:
                raise

    # ------------------------------------------------------------------
    # File index
    # ------------------------------------------------------------------

    def get_index(self) -> dict:
        return self._get_json(INDEX_PATH, {"files": {}})

    def _save_index(self, index: dict):
        self._put_json(INDEX_PATH, index)

    # ------------------------------------------------------------------
    # Saved repos
    # ------------------------------------------------------------------

    def get_repos(self) -> list[dict]:
        return self._get_json(REPOS_PATH, {"repos": []})["repos"]

    def save_repo(self, url: str, name: str, description: str = "") -> None:
        data = self._get_json(REPOS_PATH, {"repos": []})
        # Avoid duplicates
        if not any(r["url"] == url for r in data["repos"]):
            data["repos"].append({
                "url": url,
                "name": name,
                "description": description,
                "added_at": datetime.now(timezone.utc).isoformat(),
            })
            self._put_json(REPOS_PATH, data)

    def delete_repo(self, url: str) -> None:
        data = self._get_json(REPOS_PATH, {"repos": []})
        data["repos"] = [r for r in data["repos"] if r["url"] != url]
        self._put_json(REPOS_PATH, data)

    # ------------------------------------------------------------------
    # External repo browsing (live, via GitHub API)
    # ------------------------------------------------------------------

    def get_external_repo(self, repo_name: str):
        """Return a PyGithub repo object for any public repo (owner/repo)."""
        return self._gh.get_repo(repo_name)

    # ------------------------------------------------------------------
    # File path helpers
    # ------------------------------------------------------------------

    def _file_key(self, username: str, folder: str, filename: str) -> str:
        return f"{username}/{folder}/{filename}" if folder else f"{username}/{filename}"

    def _repo_path(self, username: str, folder: str, filename: str) -> str:
        return FILES_PREFIX + self._file_key(username, folder, filename)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def upload_file(
        self,
        username: str,
        folder: str,
        filename: str,
        content: bytes,
        tags: list[str],
        description: str,
    ):
        path = self._repo_path(username, folder, filename)
        now = datetime.now(timezone.utc).isoformat()
        try:
            existing = self._repo.get_contents(path)
            result = self._repo.update_file(path, f"Upload {filename}", content, existing.sha)
        except GithubException as e:
            if e.status == 404:
                result = self._repo.create_file(path, f"Upload {filename}", content)
            else:
                raise

        sha = result["content"].sha
        index = self.get_index()
        key = self._file_key(username, folder, filename)
        index["files"][key] = {
            "owner": username,
            "folder": folder,
            "filename": filename,
            "tags": tags,
            "description": description,
            "uploaded_at": now,
            "sha": sha,
        }
        self._save_index(index)

    def get_file_content(self, username: str, folder: str, filename: str) -> str:
        path = self._repo_path(username, folder, filename)
        content = self._repo.get_contents(path)
        return content.decoded_content.decode("utf-8")

    def delete_file(self, username: str, folder: str, filename: str):
        path = self._repo_path(username, folder, filename)
        try:
            existing = self._repo.get_contents(path)
            self._repo.delete_file(path, f"Delete {filename}", existing.sha)
        except GithubException as e:
            if e.status != 404:
                raise
        index = self.get_index()
        key = self._file_key(username, folder, filename)
        index["files"].pop(key, None)
        self._save_index(index)

    def update_metadata(self, username: str, folder: str, filename: str, tags: list[str], description: str):
        index = self.get_index()
        key = self._file_key(username, folder, filename)
        if key in index["files"]:
            index["files"][key]["tags"] = tags
            index["files"][key]["description"] = description
            self._save_index(index)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_all_files(self) -> dict:
        return self.get_index()["files"]

    def get_all_folders(self) -> list[str]:
        return sorted({v.get("folder", "") for v in self.get_all_files().values() if v.get("folder")})

    def file_exists(self, username: str, folder: str, filename: str) -> bool:
        return self._file_key(username, folder, filename) in self.get_index()["files"]
