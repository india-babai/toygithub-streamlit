import hashlib
import json
import secrets as _secrets
from datetime import datetime, timezone

from github import Github, GithubException

INDEX_PATH = "_index.json"
USERS_PATH = "_users.json"
FILES_PREFIX = "files/"


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000).hex()


def _new_salt() -> str:
    return _secrets.token_hex(16)


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
    # Index
    # ------------------------------------------------------------------

    def get_index(self) -> dict:
        return self._get_json(INDEX_PATH, {"files": {}})

    def _save_index(self, index: dict):
        self._put_json(INDEX_PATH, index)

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def get_users(self) -> dict:
        return self._get_json(USERS_PATH, {"users": {}})

    def _save_users(self, users: dict):
        self._put_json(USERS_PATH, users)

    def register_user(self, username: str, password: str) -> bool:
        """Returns False if username already taken."""
        users = self.get_users()
        if username in users["users"]:
            return False
        salt = _new_salt()
        users["users"][username] = {
            "password_hash": _hash_password(password, salt),
            "salt": salt,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_users(users)
        return True

    def verify_user(self, username: str, password: str) -> bool:
        users = self.get_users()
        user = users["users"].get(username)
        if not user:
            return False
        return _hash_password(password, user["salt"]) == user["password_hash"]

    def username_exists(self, username: str) -> bool:
        return username in self.get_users()["users"]

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

    def get_user_files(self, username: str) -> dict:
        return {k: v for k, v in self.get_index()["files"].items() if v["owner"] == username}

    def get_all_files(self) -> dict:
        return self.get_index()["files"]

    def get_user_folders(self, username: str) -> list[str]:
        return sorted({v["folder"] for v in self.get_user_files(username).values() if v["folder"]})

    def file_exists(self, username: str, folder: str, filename: str) -> bool:
        return self._file_key(username, folder, filename) in self.get_index()["files"]
