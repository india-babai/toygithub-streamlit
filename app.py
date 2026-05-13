import streamlit as st
from github_storage import GitHubStorage

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = [
    "py", "js", "ts", "sql", "yaml", "yml", "json", "toml", "cfg", "ini",
    "sh", "bash", "ps1", "bat", "cmd", "md", "txt", "csv", "xml", "html",
    "css", "r", "jl", "go", "rs", "java", "kt", "scala", "c", "cpp", "h",
    "dockerfile", "makefile", "gitignore", "env",
]

LANG_MAP = {
    "py": "python", "js": "javascript", "ts": "typescript",
    "sql": "sql", "yaml": "yaml", "yml": "yaml",
    "json": "json", "toml": "toml", "md": "markdown",
    "sh": "bash", "bash": "bash", "html": "html", "css": "css",
    "r": "r", "go": "go", "rs": "rust", "java": "java",
    "kt": "kotlin", "scala": "scala", "c": "c", "cpp": "cpp",
    "h": "c", "ps1": "powershell", "xml": "xml", "csv": "text",
    "txt": "text", "cfg": "ini", "ini": "ini",
}

SHARED_USER = "shared"

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="ToyGitHub", page_icon=":file_folder:", layout="wide")

# ---------------------------------------------------------------------------
# Storage singleton
# ---------------------------------------------------------------------------

@st.cache_resource
def get_storage() -> GitHubStorage:
    return GitHubStorage(
        token=st.secrets["github_pat"],
        repo_name=st.secrets["storage_repo"],
    )

storage = get_storage()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title(":file_folder: ToyGitHub")

page = st.sidebar.radio(
    "Navigate",
    ["Browse Files", "Upload Files", "Paste Code", "Manage Files"],
    label_visibility="collapsed",
)

if st.sidebar.button("Refresh"):
    st.rerun()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ext(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    return parts[1].lower() if len(parts) == 2 else ""

def _lang(filename: str) -> str:
    return LANG_MAP.get(_ext(filename), "text")

def _tag_badges(tags: list) -> str:
    return " ".join(f"`{t}`" for t in tags) if tags else ""

def _render_file(filename: str, content: str):
    if _ext(filename) == "md":
        st.markdown(content)
    else:
        st.code(content, language=_lang(filename), line_numbers=True)

def _get_all_folders() -> list[str]:
    files = storage.get_all_files()
    return sorted({v.get("folder", "") for v in files.values() if v.get("folder")})

# ---------------------------------------------------------------------------
# Page: Browse Files
# ---------------------------------------------------------------------------

if page == "Browse Files":
    st.title("Browse Files")

    files = storage.get_all_files()

    if not files:
        st.info("No files yet. Go to **Upload Files** or **Paste Code** to add your first file.")
        st.stop()

    all_tags = sorted({t for meta in files.values() for t in meta.get("tags", [])})

    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("Search by filename", placeholder="e.g. etl_pipeline")
    with col2:
        tag_filter = st.multiselect("Filter by tag", all_tags)

    filtered = {
        k: v for k, v in files.items()
        if (not search or search.lower() in v.get("filename", k).lower())
        and (not tag_filter or any(t in v.get("tags", []) for t in tag_filter))
    }

    if not filtered:
        st.warning("No files match your filters.")
        st.stop()

    # Group by folder
    grouped: dict[str, list] = {}
    for key, meta in sorted(filtered.items()):
        folder = meta.get("folder") or "(root)"
        grouped.setdefault(folder, []).append((key, meta))

    st.caption(f"{len(filtered)} file(s) found")

    for folder_name, file_list in sorted(grouped.items()):
        with st.expander(f":open_file_folder: {folder_name}  ({len(file_list)} file(s))", expanded=True):
            for key, meta in file_list:
                filename = meta.get("filename", key.split("/")[-1])
                folder = meta.get("folder", "")
                file_owner = meta.get("owner", SHARED_USER)
                st.markdown(f"**{filename}**  {_tag_badges(meta.get('tags', []))}")
                if meta.get("description"):
                    st.caption(meta["description"])
                st.caption(f"Uploaded: {meta.get('uploaded_at', '')[:10]}")

                load_key = f"load_{key}"
                if st.button("Load", key=f"btn_{key}"):
                    st.session_state[load_key] = True

                if st.session_state.get(load_key):
                    with st.spinner("Fetching..."):
                        try:
                            content = storage.get_file_content(file_owner, folder, filename)
                        except Exception as e:
                            st.error(f"Failed to load: {e}")
                            continue
                    _render_file(filename, content)

                st.divider()

# ---------------------------------------------------------------------------
# Page: Upload Files
# ---------------------------------------------------------------------------

elif page == "Upload Files":
    st.title("Upload Files")

    existing_folders = _get_all_folders()
    folder_options = ["(root)"] + existing_folders + ["+ New folder..."]
    folder_choice = st.selectbox("Upload to folder", folder_options)

    if folder_choice == "+ New folder...":
        new_folder = st.text_input("New folder name", placeholder="e.g. work-project")
        folder = new_folder.strip().replace(" ", "-") if new_folder.strip() else ""
    elif folder_choice == "(root)":
        folder = ""
    else:
        folder = folder_choice

    st.divider()

    uploaded_files = st.file_uploader(
        "Drag and drop files here (or click to browse)",
        type=ALLOWED_EXTENSIONS,
        accept_multiple_files=True,
    )

    if uploaded_files:
        tags_input = st.text_input("Tags for all files (comma-separated)", placeholder="e.g. python, etl")
        description = st.text_area("Description (optional, applies to all)", height=70)
        tags = [t.strip() for t in tags_input.split(",") if t.strip()]

        st.caption(f"{len(uploaded_files)} file(s) selected → folder: **{folder or '(root)'}**")

        if st.button("Upload All", type="primary"):
            results = []
            for uf in uploaded_files:
                raw = uf.read()
                try:
                    raw.decode("utf-8")
                except UnicodeDecodeError:
                    results.append((uf.name, False, "Not a text file — skipped."))
                    continue
                try:
                    storage.upload_file(SHARED_USER, folder, uf.name, raw, tags, description)
                    results.append((uf.name, True, ""))
                except Exception as e:
                    results.append((uf.name, False, str(e)))

            for name, ok, err in results:
                if ok:
                    st.success(f"**{name}** uploaded.")
                else:
                    st.error(f"**{name}**: {err}")

# ---------------------------------------------------------------------------
# Page: Paste Code
# ---------------------------------------------------------------------------

elif page == "Paste Code":
    st.title("Paste Code")

    col1, col2 = st.columns([2, 1])
    with col1:
        filename = st.text_input("Filename (include extension)", placeholder="e.g. etl_pipeline.py")
    with col2:
        existing_folders = _get_all_folders()
        folder_options = ["(root)"] + existing_folders + ["+ New folder..."]
        folder_choice = st.selectbox("Folder", folder_options, key="paste_folder")

    if folder_choice == "+ New folder...":
        new_folder = st.text_input("New folder name", placeholder="e.g. work-project", key="paste_new_folder")
        folder = new_folder.strip().replace(" ", "-") if new_folder.strip() else ""
    elif folder_choice == "(root)":
        folder = ""
    else:
        folder = folder_choice

    pasted = st.text_area(
        "Paste your code or text here",
        height=400,
        placeholder="Paste code here...",
    )

    tags_input = st.text_input("Tags (comma-separated)", placeholder="e.g. python, etl", key="paste_tags")
    description = st.text_area("Description (optional)", height=70, key="paste_desc")

    if st.button("Save", type="primary", key="paste_save"):
        if not filename:
            st.error("Please enter a filename.")
        elif not pasted.strip():
            st.error("Nothing to save — paste some content first.")
        else:
            tags = [t.strip() for t in tags_input.split(",") if t.strip()]
            raw = pasted.encode("utf-8")
            if storage.file_exists(SHARED_USER, folder, filename):
                st.warning(f"**{filename}** already exists and will be overwritten.")
            with st.spinner("Saving..."):
                try:
                    storage.upload_file(SHARED_USER, folder, filename, raw, tags, description)
                    st.success(f"**{filename}** saved successfully.")
                except Exception as e:
                    st.error(f"Failed to save: {e}")

    if pasted.strip() and filename:
        st.divider()
        st.caption("Preview")
        _render_file(filename, pasted)

# ---------------------------------------------------------------------------
# Page: Manage Files
# ---------------------------------------------------------------------------

elif page == "Manage Files":
    st.title("Manage Files")

    files = storage.get_all_files()

    if not files:
        st.info("No files yet.")
        st.stop()

    grouped: dict[str, list] = {}
    for key, meta in sorted(files.items()):
        folder_name = meta.get("folder") or "(root)"
        grouped.setdefault(folder_name, []).append((key, meta))

    for folder_name, file_list in sorted(grouped.items()):
        st.subheader(f":open_file_folder: {folder_name}")
        for key, meta in file_list:
            filename = meta.get("filename", key.split("/")[-1])
            folder = meta.get("folder", "")
            file_owner = meta.get("owner", SHARED_USER)
            with st.expander(f"**{filename}**  {_tag_badges(meta.get('tags', []))}"):
                with st.form(key=f"edit_{key}"):
                    new_tags_input = st.text_input("Tags", value=", ".join(meta.get("tags", [])))
                    new_desc = st.text_area("Description", value=meta.get("description", ""), height=70)
                    save_btn = st.form_submit_button("Save changes")
                    del_btn = st.form_submit_button("Delete file", type="secondary")

                if save_btn:
                    new_tags = [t.strip() for t in new_tags_input.split(",") if t.strip()]
                    with st.spinner("Saving..."):
                        try:
                            storage.update_metadata(file_owner, folder, filename, new_tags, new_desc)
                            st.success("Updated.")
                        except Exception as e:
                            st.error(str(e))

                if del_btn:
                    st.session_state[f"confirm_{key}"] = True

                if st.session_state.get(f"confirm_{key}"):
                    st.warning(f"Delete **{filename}**? This cannot be undone.")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Yes, delete", key=f"yes_{key}", type="primary"):
                            with st.spinner("Deleting..."):
                                try:
                                    storage.delete_file(file_owner, folder, filename)
                                    st.session_state.pop(f"confirm_{key}", None)
                                    st.success("Deleted.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))
                    with c2:
                        if st.button("Cancel", key=f"cancel_{key}"):
                            st.session_state.pop(f"confirm_{key}", None)
                            st.rerun()
