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

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ToyGitHub",
    page_icon=":file_folder:",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title(":lock: ToyGitHub")
    st.caption("Private code sharing — enter the password to continue.")
    pwd = st.text_input("Password", type="password", key="login_pwd")
    if st.button("Enter", type="primary"):
        if pwd == st.secrets["app_password"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()

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
# Sidebar navigation
# ---------------------------------------------------------------------------

st.sidebar.title(":file_folder: ToyGitHub")
page = st.sidebar.radio(
    "Navigate",
    ["Browse Files", "Upload File", "Manage Files"],
    label_visibility="collapsed",
)

if st.sidebar.button("Refresh index"):
    storage.get_index(force_refresh=True)
    st.sidebar.success("Refreshed.")

st.sidebar.divider()
if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ext(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    return parts[1].lower() if len(parts) == 2 else ""

def _lang(filename: str) -> str:
    return LANG_MAP.get(_ext(filename), "text")

def _tag_badges(tags: list[str]) -> str:
    if not tags:
        return ""
    return " ".join(f"`{t}`" for t in tags)

def _render_file(filename: str, content: str):
    ext = _ext(filename)
    if ext == "md":
        st.markdown(content)
    else:
        st.code(content, language=_lang(filename), line_numbers=True)

# ---------------------------------------------------------------------------
# Page: Browse Files
# ---------------------------------------------------------------------------

if page == "Browse Files":
    st.title("Browse Files")

    index = storage.get_index()
    files = index["files"]

    if not files:
        st.info("No files uploaded yet. Go to **Upload File** to add your first file.")
        st.stop()

    # Collect all tags
    all_tags = sorted({t for meta in files.values() for t in meta["tags"]})

    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("Search by filename", placeholder="e.g. etl_pipeline")
    with col2:
        tag_filter = st.multiselect("Filter by tag", all_tags)

    # Filter
    filtered = {
        name: meta for name, meta in files.items()
        if (not search or search.lower() in name.lower())
        and (not tag_filter or any(t in meta["tags"] for t in tag_filter))
    }

    if not filtered:
        st.warning("No files match your filters.")
        st.stop()

    st.caption(f"{len(filtered)} file(s) found")
    st.divider()

    for filename, meta in sorted(filtered.items()):
        with st.expander(f"**{filename}**  {_tag_badges(meta['tags'])}"):
            desc = meta.get("description", "")
            uploaded_at = meta.get("uploaded_at", "")[:10]

            col_a, col_b = st.columns([3, 1])
            with col_a:
                if desc:
                    st.caption(desc)
                st.caption(f"Uploaded: {uploaded_at}")
            with col_b:
                load_key = f"load_{filename}"
                if st.button("Load file", key=f"btn_{filename}"):
                    st.session_state[load_key] = True

            if st.session_state.get(load_key):
                with st.spinner("Fetching from GitHub..."):
                    try:
                        content = storage.get_file_content(filename)
                        raw_bytes = content.encode("utf-8")
                    except Exception as e:
                        st.error(f"Failed to load file: {e}")
                        continue

                _render_file(filename, content)

                st.download_button(
                    label="Download",
                    data=raw_bytes,
                    file_name=filename,
                    mime="text/plain",
                    key=f"dl_{filename}",
                )

# ---------------------------------------------------------------------------
# Page: Upload File
# ---------------------------------------------------------------------------

elif page == "Upload File":
    st.title("Upload File")

    uploaded = st.file_uploader(
        "Choose a file",
        type=ALLOWED_EXTENSIONS,
        accept_multiple_files=False,
    )

    if uploaded is not None:
        raw_bytes = uploaded.read()
        try:
            content_str = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            st.error("File does not appear to be a text file. Only text/code files are supported.")
            st.stop()

        filename = uploaded.name

        st.subheader("Preview")
        _render_file(filename, content_str)

        st.divider()

        tags_input = st.text_input(
            "Tags (comma-separated)",
            placeholder="e.g. python, etl, work",
        )
        description = st.text_area(
            "Description (optional)",
            placeholder="Brief note about this file",
            height=80,
        )

        tags = [t.strip() for t in tags_input.split(",") if t.strip()]

        already_exists = storage.file_exists(filename)
        if already_exists:
            st.warning(f"**{filename}** already exists. Uploading will overwrite it.")

        btn_label = "Overwrite" if already_exists else "Upload"
        if st.button(btn_label, type="primary"):
            with st.spinner("Uploading to GitHub..."):
                try:
                    storage.upload_file(filename, raw_bytes, tags, description)
                    st.success(f"**{filename}** uploaded successfully.")
                except Exception as e:
                    st.error(f"Upload failed: {e}")

# ---------------------------------------------------------------------------
# Page: Manage Files
# ---------------------------------------------------------------------------

elif page == "Manage Files":
    st.title("Manage Files")

    index = storage.get_index()
    files = index["files"]

    if not files:
        st.info("No files to manage yet.")
        st.stop()

    for filename, meta in sorted(files.items()):
        with st.expander(f"**{filename}**  {_tag_badges(meta['tags'])}"):
            desc = meta.get("description", "")
            uploaded_at = meta.get("uploaded_at", "")[:10]
            st.caption(f"Uploaded: {uploaded_at}")

            # Edit metadata form
            with st.form(key=f"edit_{filename}"):
                new_tags_input = st.text_input(
                    "Tags",
                    value=", ".join(meta["tags"]),
                    key=f"tags_{filename}",
                )
                new_desc = st.text_area(
                    "Description",
                    value=desc,
                    height=70,
                    key=f"desc_{filename}",
                )
                save_col, del_col = st.columns([1, 1])
                with save_col:
                    save = st.form_submit_button("Save changes")
                with del_col:
                    confirm_key = f"confirm_del_{filename}"
                    delete = st.form_submit_button("Delete file", type="secondary")

            if save:
                new_tags = [t.strip() for t in new_tags_input.split(",") if t.strip()]
                with st.spinner("Saving..."):
                    try:
                        storage.update_metadata(filename, new_tags, new_desc)
                        st.success("Metadata updated.")
                    except Exception as e:
                        st.error(f"Failed to update: {e}")

            if delete:
                st.session_state[f"confirm_del_{filename}"] = True

            if st.session_state.get(f"confirm_del_{filename}"):
                st.warning(f"Are you sure you want to delete **{filename}**? This cannot be undone.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Yes, delete", key=f"yes_del_{filename}", type="primary"):
                        with st.spinner("Deleting..."):
                            try:
                                storage.delete_file(filename)
                                st.session_state.pop(f"confirm_del_{filename}", None)
                                st.success(f"**{filename}** deleted.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Delete failed: {e}")
                with c2:
                    if st.button("Cancel", key=f"cancel_del_{filename}"):
                        st.session_state.pop(f"confirm_del_{filename}", None)
                        st.rerun()
