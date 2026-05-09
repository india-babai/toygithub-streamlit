import json
from datetime import datetime, timezone

import streamlit as st
from github import Github, GithubException

INDEX_PATH = "_index.json"
FILES_PREFIX = "files/"
_SESSION_KEY = "_tgh_index"


class GitHubStorage:
    def __init__(self, token: str, repo_name: str):
        self._gh = Github(token)
        self._repo = self._gh.get_repo(repo_name)

    # ------------------------------------------------------------------
    # Index helpers
    # ------------------------------------------------------------------

    def _load_index(self) -> dict:
        try:
            content = self._repo.get_contents(INDEX_PATH)
            return json.loads(content.decoded_content.decode("utf-8"))
        except GithubException as e:
            if e.status == 404:
                return {"files": {}}
            raise

    def _save_index(self, index: dict):
        data = json.dumps(index, indent=2, ensure_ascii=False).encode("utf-8")
        try:
            existing = self._repo.get_contents(INDEX_PATH)
            self._repo.update_file(INDEX_PATH, "Update index", data, existing.sha)
        except GithubException as e:
            if e.status == 404:
                self._repo.create_file(INDEX_PATH, "Create index", data)
            else:
                raise

    def get_index(self, force_refresh: bool = False) -> dict:
        if force_refresh or _SESSION_KEY not in st.session_state:
            st.session_state[_SESSION_KEY] = self._load_index()
        return st.session_state[_SESSION_KEY]

    def _invalidate_cache(self):
        st.session_state.pop(_SESSION_KEY, None)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def upload_file(
        self,
        filename: str,
        content: bytes,
        tags: list[str],
        description: str,
    ):
        path = FILES_PREFIX + filename
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
        index["files"][filename] = {
            "tags": tags,
            "description": description,
            "uploaded_at": now,
            "sha": sha,
        }
        self._save_index(index)
        self._invalidate_cache()

    def get_file_content(self, filename: str) -> str:
        path = FILES_PREFIX + filename
        content = self._repo.get_contents(path)
        return content.decoded_content.decode("utf-8")

    def get_file_bytes(self, filename: str) -> bytes:
        path = FILES_PREFIX + filename
        content = self._repo.get_contents(path)
        return content.decoded_content

    def delete_file(self, filename: str):
        path = FILES_PREFIX + filename
        try:
            existing = self._repo.get_contents(path)
            self._repo.delete_file(path, f"Delete {filename}", existing.sha)
        except GithubException as e:
            if e.status != 404:
                raise
        index = self.get_index()
        index["files"].pop(filename, None)
        self._save_index(index)
        self._invalidate_cache()

    def update_metadata(self, filename: str, tags: list[str], description: str):
        index = self.get_index()
        if filename in index["files"]:
            index["files"][filename]["tags"] = tags
            index["files"][filename]["description"] = description
            self._save_index(index)
            self._invalidate_cache()

    def file_exists(self, filename: str) -> bool:
        return filename in self.get_index()["files"]
