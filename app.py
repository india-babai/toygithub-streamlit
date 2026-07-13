import re
import requests
import streamlit as st
from github import GithubException
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

NAV_PAGES = [
    ("home",   "🏠", "Home"),
    ("browse", "🔍", "Browse Files"),
    ("repos",  "🐙", "GitHub Repos"),
    ("upload", "⬆️",  "Upload Files"),
    ("paste",  "📋", "Paste Code"),
    ("manage", "🗂️",  "Manage Files"),
]

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ToyGitHub",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
/* ── Sidebar nav ─────────────────────────────────────── */
section[data-testid="stSidebar"] .stButton > button {
    border: none !important;
    background: transparent !important;
    text-align: left !important;
    width: 100% !important;
    padding: 0.45rem 1.1rem !important;
    border-radius: 8px !important;
    font-size: 0.95rem !important;
    color: #475569 !important;
    font-weight: 400 !important;
    transition: background 0.15s, color 0.15s !important;
    margin-bottom: 1px !important;
    box-shadow: none !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(74,144,217,0.1) !important;
    color: #2563EB !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(74,144,217,0.15) !important;
    color: #2563EB !important;
    font-weight: 600 !important;
    border-left: 3px solid #2563EB !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: rgba(74,144,217,0.22) !important;
}

/* ── Tag pills ───────────────────────────────────────── */
.tg-pill {
    display: inline-block;
    background: #EFF6FF;
    color: #2563EB;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.76rem;
    font-weight: 500;
    margin-right: 4px;
    margin-bottom: 2px;
    border: 1px solid #BFDBFE;
}

/* ── Page header ─────────────────────────────────────── */
.pg-header { margin-bottom: 1.5rem; }
.pg-header h2 { margin-bottom: 0.1rem; }
.pg-subtitle {
    color: #64748b;
    font-size: 0.97rem;
    margin-top: 0;
}

/* ── Hero (landing) ──────────────────────────────────── */
.hero-title {
    font-size: 2.8rem;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.15;
    margin-bottom: 0.4rem;
}
.hero-sub {
    font-size: 1.15rem;
    color: #475569;
    margin-bottom: 0;
}

/* ── Feature card (landing) ──────────────────────────── */
.feat-card {
    background: linear-gradient(135deg, #f8faff 0%, #eff6ff 100%);
    border: 1px solid #dbeafe;
    border-radius: 14px;
    padding: 1.6rem 1.4rem;
    height: 100%;
    text-align: center;
}
.feat-icon { font-size: 2rem; margin-bottom: 0.4rem; }
.feat-title { font-weight: 700; font-size: 1rem; color: #1e3a5f; margin-bottom: 0.3rem; }
.feat-desc  { font-size: 0.87rem; color: #64748b; }

/* ── Step badge ──────────────────────────────────────── */
.step-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px; height: 26px;
    background: #2563EB;
    color: white;
    border-radius: 50%;
    font-size: 0.82rem;
    font-weight: 700;
    margin-right: 8px;
    vertical-align: middle;
}

/* ── File meta line ──────────────────────────────────── */
.file-meta { font-size: 0.82rem; color: #94a3b8; margin-top: 4px; }

/* ── Stat number ─────────────────────────────────────── */
.stat-num { font-size: 2.2rem; font-weight: 800; color: #2563EB; line-height: 1; }
.stat-lbl { font-size: 0.82rem; color: #64748b; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

@st.cache_resource
def get_storage() -> GitHubStorage:
    return GitHubStorage(
        token=st.secrets["github_pat"],
        repo_name=st.secrets["storage_repo"],
    )

storage = get_storage()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "page" not in st.session_state:
    st.session_state.page = "home"

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 📁 ToyGitHub")
    st.caption("Your private code shelf")
    st.divider()

    for key, icon, label in NAV_PAGES:
        active = st.session_state.page == key
        if st.button(
            f"{icon}  {label}",
            key=f"nav_{key}",
            use_container_width=True,
            type="primary" if active else "secondary",
        ):
            st.session_state.page = key
            st.rerun()

    st.divider()
    if st.button("🔄  Refresh data", use_container_width=True):
        for k in list(st.session_state.keys()):
            if k.startswith(("repo_tree_", "file_content_", "repo_zip_")):
                del st.session_state[k]
        st.rerun()

page = st.session_state.page

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _go(p: str):
    st.session_state.page = p
    st.rerun()

def _ext(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    return parts[1].lower() if len(parts) == 2 else ""

def _lang(filename: str) -> str:
    return LANG_MAP.get(_ext(filename), "text")

def _pills(tags: list) -> str:
    if not tags:
        return ""
    return " ".join(f'<span class="tg-pill">{t}</span>' for t in tags)

def _render(filename: str, content: str):
    if _ext(filename) == "md":
        st.markdown(content)
    else:
        st.code(content, language=_lang(filename), line_numbers=True)

def _page_header(icon: str, title: str, subtitle: str):
    st.markdown(
        f'<div class="pg-header">'
        f'<h2>{icon} {title}</h2>'
        f'<p class="pg-subtitle">{subtitle}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

def _parse_github_url(url: str) -> str | None:
    url = url.strip().rstrip("/")
    match = re.search(r"github\.com/([^/\s]+/[^/\s]+)", url)
    if match:
        return match.group(1).removesuffix(".git")
    return None

def _build_tree(paths: list[str]) -> dict:
    tree = {}
    for path in sorted(paths):
        parts = path.split("/")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = None
    return tree

def _render_tree(tree: dict, prefix: str = "", depth: int = 0):
    folders = sorted(k for k, v in tree.items() if v is not None)
    files   = sorted(k for k, v in tree.items() if v is None)
    for folder in folders:
        with st.expander(f"📁 **{folder}**", expanded=(depth == 0)):
            _render_tree(tree[folder], prefix + folder + "/", depth + 1)
    for filename in files:
        full_path = prefix + filename
        if st.button(f"📄 {filename}", key=f"tree_{full_path}", use_container_width=True):
            st.session_state["selected_file_path"] = full_path

# ===========================================================================
# PAGE: HOME
# ===========================================================================

if page == "home":
    # Hero
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown('<p class="hero-title">📁 ToyGitHub</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="hero-sub">Your private code shelf — upload, browse, and share code files '
            'across any network, no GitHub access required on the other end.</p>',
            unsafe_allow_html=True,
        )
        st.markdown("")
        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            if st.button("🔍  Browse Files", use_container_width=True, type="primary"):
                _go("browse")
        with bc2:
            if st.button("🐙  GitHub Repos", use_container_width=True):
                _go("repos")
        with bc3:
            if st.button("⬆️  Upload Files", use_container_width=True):
                _go("upload")

    st.divider()

    # Feature cards
    f1, f2, f3, f4 = st.columns(4)
    features = [
        ("🔍", "Browse Files",    "View all your uploaded code with syntax highlighting and tag filters."),
        ("🐙", "GitHub Repos",   "Paste any public GitHub URL and browse its full folder & file structure live."),
        ("⬆️",  "Upload Files",   "Drag-and-drop multiple files at once into organised folders."),
        ("📋", "Paste Code",     "Paste a snippet directly into the app — no file needed."),
    ]
    for col, (icon, title, desc) in zip([f1, f2, f3, f4], features):
        with col:
            st.markdown(
                f'<div class="feat-card">'
                f'<div class="feat-icon">{icon}</div>'
                f'<div class="feat-title">{title}</div>'
                f'<div class="feat-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("")

    # Live stats
    st.markdown("### 📊 At a glance")
    try:
        all_files = storage.get_all_files()
        all_repos = storage.get_repos()
        all_folders = storage.get_all_folders()
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            with st.container(border=True):
                st.markdown(f'<div class="stat-num">{len(all_files)}</div><div class="stat-lbl">Files stored</div>', unsafe_allow_html=True)
        with s2:
            with st.container(border=True):
                st.markdown(f'<div class="stat-num">{len(all_repos)}</div><div class="stat-lbl">GitHub repos saved</div>', unsafe_allow_html=True)
        with s3:
            with st.container(border=True):
                st.markdown(f'<div class="stat-num">{len(all_folders)}</div><div class="stat-lbl">Folders</div>', unsafe_allow_html=True)
        with s4:
            all_tags = {t for m in all_files.values() for t in m.get("tags", [])}
            with st.container(border=True):
                st.markdown(f'<div class="stat-num">{len(all_tags)}</div><div class="stat-lbl">Unique tags</div>', unsafe_allow_html=True)
    except Exception:
        st.info("Could not load stats — check your connection.")

# ===========================================================================
# PAGE: BROWSE FILES
# ===========================================================================

elif page == "browse":
    _page_header("🔍", "Browse Files", "Search and view all uploaded files with syntax highlighting.")

    files = storage.get_all_files()

    if not files:
        st.info("No files yet. Head to **Upload Files** or **Paste Code** to get started.")
        if st.button("⬆️  Upload your first file", type="primary"):
            _go("upload")
        st.stop()

    all_tags = sorted({t for meta in files.values() for t in meta.get("tags", [])})

    with st.container(border=True):
        fc1, fc2 = st.columns([3, 1])
        with fc1:
            search = st.text_input("🔎  Search by filename", placeholder="e.g. etl_pipeline, config…", label_visibility="collapsed")
        with fc2:
            tag_filter = st.multiselect("Tags", all_tags, placeholder="Filter by tag…")

    filtered = {
        k: v for k, v in files.items()
        if (not search or search.lower() in v.get("filename", k).lower())
        and (not tag_filter or any(t in v.get("tags", []) for t in tag_filter))
    }

    if not filtered:
        st.warning("No files match your filters.")
        st.stop()

    grouped: dict[str, list] = {}
    for key, meta in sorted(filtered.items()):
        folder = meta.get("folder") or "(root)"
        grouped.setdefault(folder, []).append((key, meta))

    st.caption(f"{len(filtered)} file(s) found across {len(grouped)} folder(s)")
    st.markdown("")

    for folder_name, file_list in sorted(grouped.items()):
        st.markdown(f"##### 📂 {folder_name}")
        for key, meta in file_list:
            filename  = meta.get("filename", key.split("/")[-1])
            folder    = meta.get("folder", "")
            owner     = meta.get("owner", SHARED_USER)
            tags      = meta.get("tags", [])
            desc      = meta.get("description", "")
            date      = meta.get("uploaded_at", "")[:10]

            with st.container(border=True):
                left, right = st.columns([5, 1])
                with left:
                    st.markdown(f"**📄 {filename}**")
                    if tags:
                        st.markdown(_pills(tags), unsafe_allow_html=True)
                    if desc:
                        st.markdown(f"<span style='color:#64748b;font-size:0.88rem'>{desc}</span>", unsafe_allow_html=True)
                    st.markdown(f'<div class="file-meta">Uploaded {date}</div>', unsafe_allow_html=True)
                with right:
                    load_key = f"load_{key}"
                    if st.button("Load", key=f"btn_{key}", use_container_width=True, type="primary"):
                        st.session_state[load_key] = True

            if st.session_state.get(load_key):
                with st.spinner(f"Fetching {filename}…"):
                    try:
                        content = storage.get_file_content(owner, folder, filename)
                    except Exception as e:
                        st.error(f"Failed to load: {e}")
                        continue
                with st.expander(f"📄 {filename}", expanded=True):
                    _render(filename, content)

        st.markdown("")

# ===========================================================================
# PAGE: GITHUB REPOS
# ===========================================================================

elif page == "repos":
    _page_header("🐙", "GitHub Repos", "Browse any public GitHub repository live — folder tree, file viewer, syntax highlighting.")

    saved_repos = storage.get_repos()

    # ── Step 1: Add a repo ──────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown('<span class="step-badge">1</span> **Add a public GitHub repository**', unsafe_allow_html=True)
        st.caption("Paste the URL of any public GitHub repo. It will be saved for future visits.")
        st.markdown("")
        col_url, col_desc, col_btn = st.columns([3, 2, 1])
        with col_url:
            new_url = st.text_input(
                "GitHub repository URL",
                placeholder="https://github.com/owner/repo-name",
                label_visibility="visible",
            )
        with col_desc:
            new_desc = st.text_input("Short description (optional)", placeholder="e.g. My ETL project")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)  # vertical align
            add_clicked = st.button("➕  Add repo", type="primary", use_container_width=True)

    if add_clicked:
        if not new_url.strip():
            st.error("Please paste a GitHub URL first.")
        else:
            repo_id = _parse_github_url(new_url.strip())
            if not repo_id:
                st.error("Could not parse that URL. Expected format: `https://github.com/owner/repo`")
            else:
                with st.spinner(f"Connecting to {repo_id}…"):
                    try:
                        storage.get_external_repo(repo_id)
                        storage.save_repo(new_url.strip(), repo_id.split("/")[-1], new_desc.strip())
                        st.session_state["active_repo"] = repo_id
                        for k in list(st.session_state.keys()):
                            if k.startswith(("repo_tree_", "file_content_", "selected_file", "repo_zip_")):
                                del st.session_state[k]
                        st.success(f"**{repo_id}** added!")
                        st.rerun()
                    except GithubException:
                        st.error("Repo not found or not accessible. Make sure it is a public repository.")

    if not saved_repos:
        st.markdown("")
        st.info("No repos saved yet — add one above to get started.")
        st.stop()

    # ── Step 2: Select a repo ───────────────────────────────────────────────
    st.markdown("")
    with st.container(border=True):
        st.markdown('<span class="step-badge">2</span> **Select a saved repository to browse**', unsafe_allow_html=True)
        st.caption("Choose from the list of repositories you have previously added.")
        st.markdown("")

        repo_labels = [f"{r['name']}  —  {r['url']}" for r in saved_repos]
        active_repo_id = st.session_state.get("active_repo")
        default_idx = 0
        if active_repo_id:
            for i, r in enumerate(saved_repos):
                if _parse_github_url(r["url"]) == active_repo_id:
                    default_idx = i
                    break

        sel_col, del_col = st.columns([6, 1])
        with sel_col:
            chosen_idx = st.selectbox(
                "Select a saved repository:",
                range(len(saved_repos)),
                format_func=lambda i: repo_labels[i],
                index=default_idx,
            )
        with del_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Remove", use_container_width=True):
                storage.delete_repo(saved_repos[chosen_idx]["url"])
                for k in list(st.session_state.keys()):
                    if k.startswith(("active_repo", "repo_tree_", "file_content_", "selected_file", "repo_zip_")):
                        del st.session_state[k]
                st.rerun()

        chosen = saved_repos[chosen_idx]
        chosen_id = _parse_github_url(chosen["url"])
        if chosen.get("description"):
            st.caption(f"_{chosen['description']}_")
        st.markdown(f"[🔗 Open on GitHub]({chosen['url']})")

    # Detect repo switch
    if st.session_state.get("active_repo") != chosen_id:
        st.session_state["active_repo"] = chosen_id
        for k in list(st.session_state.keys()):
            if k.startswith(("repo_tree_", "file_content_", "selected_file", "repo_zip_")):
                del st.session_state[k]

    st.markdown("")

    # ── Step 3: Browse ──────────────────────────────────────────────────────
    cache_key = f"repo_tree_{chosen_id}"
    if cache_key not in st.session_state:
        with st.spinner(f"Fetching file tree for **{chosen_id}**…"):
            try:
                ext_repo = storage.get_external_repo(chosen_id)
                tree_obj = ext_repo.get_git_tree(ext_repo.default_branch, recursive=True)
                all_paths = [i.path for i in tree_obj.tree if i.type == "blob"]
                st.session_state[cache_key] = all_paths
            except GithubException as e:
                st.error(f"Failed to fetch repo tree: {e}")
                st.stop()

    all_paths = st.session_state[cache_key]
    file_tree = _build_tree(all_paths)

    tree_col, viewer_col = st.columns([1, 2])

    with tree_col:
        with st.container(border=True):
            hdr_col, refresh_col = st.columns([3, 1])
            with hdr_col:
                st.markdown(f"**📁 {chosen_id}**")
                st.caption(f"{len(all_paths)} files · click a file to view it")
            with refresh_col:
                if st.button("🔄", key="refresh_repo", help="Re-fetch this repo from GitHub (picks up new commits)", use_container_width=True):
                    for k in list(st.session_state.keys()):
                        if k.startswith(("repo_tree_", "file_content_", "selected_file", "repo_zip_")):
                            del st.session_state[k]
                    st.rerun()

            # ── Download entire repo as ZIP ──────────────────────────
            zip_key = f"repo_zip_{chosen_id}"
            if zip_key in st.session_state:
                st.download_button(
                    "💾  Download ZIP",
                    data=st.session_state[zip_key],
                    file_name=f"{chosen_id.replace('/', '-')}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    type="primary",
                )
                st.caption(f"Archive ready ({len(st.session_state[zip_key]) / 1024 / 1024:.1f} MB) — click to save.")
            else:
                if st.button("📦  Prepare ZIP of entire repo", use_container_width=True):
                    with st.spinner(f"Fetching archive of {chosen_id}…"):
                        try:
                            ext_repo = storage.get_external_repo(chosen_id)
                            zip_url = ext_repo.get_archive_link("zipball")
                            resp = requests.get(zip_url, timeout=120)
                            resp.raise_for_status()
                            # Keep at most one prepared archive in memory
                            for k in list(st.session_state.keys()):
                                if k.startswith("repo_zip_"):
                                    del st.session_state[k]
                            st.session_state[zip_key] = resp.content
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to fetch archive: {e}")

            st.divider()
            _render_tree(file_tree)

    with viewer_col:
        selected = st.session_state.get("selected_file_path")
        if selected:
            vcache = f"file_content_{chosen_id}_{selected}"
            if vcache not in st.session_state:
                with st.spinner(f"Loading `{selected}`…"):
                    try:
                        ext_repo = storage.get_external_repo(chosen_id)
                        obj = ext_repo.get_contents(selected)
                        try:
                            st.session_state[vcache] = obj.decoded_content.decode("utf-8")
                        except UnicodeDecodeError:
                            st.session_state[vcache] = "__binary__"
                    except GithubException as e:
                        st.error(f"Could not load file: {e}")
                        st.stop()

            with st.container(border=True):
                st.markdown(f"**`{selected}`**")
                st.divider()
                content = st.session_state[vcache]
                if content == "__binary__":
                    st.warning("Binary file — cannot display.")
                else:
                    _render(selected.split("/")[-1], content)
        else:
            with st.container(border=True):
                st.markdown("")
                st.markdown(
                    "<div style='text-align:center;padding:3rem 1rem;color:#94a3b8'>"
                    "<div style='font-size:3rem'>📄</div>"
                    "<div style='margin-top:0.5rem'>Select a file from the tree on the left to view it here</div>"
                    "</div>",
                    unsafe_allow_html=True,
                )

# ===========================================================================
# PAGE: UPLOAD FILES
# ===========================================================================

elif page == "upload":
    _page_header("⬆️", "Upload Files", "Drag and drop one or more files into a folder. Supports 25+ file types including Python, SQL, Markdown, JS, YAML and more.")

    all_folders = storage.get_all_folders()

    with st.container(border=True):
        st.markdown("**📂 Choose a destination folder**")
        folder_options = ["(root — no folder)"] + all_folders + ["＋ Create new folder…"]
        folder_choice = st.selectbox("Destination folder", folder_options, label_visibility="collapsed")

        if folder_choice == "＋ Create new folder…":
            new_folder = st.text_input("New folder name", placeholder="e.g. work-project, scripts…")
            folder = new_folder.strip().replace(" ", "-") if new_folder.strip() else ""
        elif folder_choice == "(root — no folder)":
            folder = ""
        else:
            folder = folder_choice

    st.markdown("")

    with st.container(border=True):
        st.markdown("**📎 Select files to upload**")
        st.caption("You can select multiple files at once. Text / code files only — binary files will be skipped.")
        uploaded_files = st.file_uploader(
            "Drop files here",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

    if uploaded_files:
        st.markdown("")
        with st.container(border=True):
            st.markdown("**🏷️ Add metadata** _(optional — applies to all files in this batch)_")
            m1, m2 = st.columns(2)
            with m1:
                tags_input = st.text_input("Tags", placeholder="python, etl, work  (comma-separated)")
            with m2:
                description = st.text_input("Description", placeholder="Brief note about these files")

        tags = [t.strip() for t in tags_input.split(",") if t.strip()]
        st.markdown("")
        dest = f"**{folder}**" if folder else "**root**"
        st.info(f"📦 {len(uploaded_files)} file(s) ready to upload → {dest}")

        if st.button("⬆️  Upload All", type="primary", use_container_width=True):
            for uf in uploaded_files:
                raw = uf.read()
                try:
                    raw.decode("utf-8")
                except UnicodeDecodeError:
                    st.warning(f"⏭️ **{uf.name}** skipped — binary file.")
                    continue
                try:
                    storage.upload_file(SHARED_USER, folder, uf.name, raw, tags, description)
                    st.success(f"✅ **{uf.name}** uploaded.")
                except Exception as e:
                    st.error(f"❌ **{uf.name}**: {e}")

# ===========================================================================
# PAGE: PASTE CODE
# ===========================================================================

elif page == "paste":
    _page_header("📋", "Paste Code", "Paste a code snippet or any text directly — no file needed. Give it a filename, choose a folder, and save.")

    with st.container(border=True):
        st.markdown("**📝 File details**")
        pc1, pc2 = st.columns([2, 1])
        with pc1:
            filename = st.text_input(
                "Filename (must include extension)",
                placeholder="e.g.  etl_pipeline.py,  config.yaml,  notes.md",
            )
        with pc2:
            all_folders = storage.get_all_folders()
            folder_options = ["(root — no folder)"] + all_folders + ["＋ Create new folder…"]
            folder_choice = st.selectbox("Destination folder", folder_options)

        if folder_choice == "＋ Create new folder…":
            new_folder = st.text_input("New folder name", placeholder="e.g. work-project", key="paste_nf")
            folder = new_folder.strip().replace(" ", "-") if new_folder.strip() else ""
        elif folder_choice == "(root — no folder)":
            folder = ""
        else:
            folder = folder_choice

    st.markdown("")

    with st.container(border=True):
        st.markdown("**💬 Paste your content**")
        pasted = st.text_area(
            "Content",
            height=350,
            placeholder="Paste code or text here…",
            label_visibility="collapsed",
        )

    st.markdown("")

    with st.container(border=True):
        st.markdown("**🏷️ Metadata** _(optional)_")
        pm1, pm2 = st.columns(2)
        with pm1:
            tags_input = st.text_input("Tags", placeholder="python, snippet  (comma-separated)", key="paste_tags")
        with pm2:
            description = st.text_input("Description", placeholder="What is this?", key="paste_desc")

    st.markdown("")

    if st.button("💾  Save", type="primary", use_container_width=True):
        if not filename:
            st.error("Please enter a filename (with extension).")
        elif not pasted.strip():
            st.error("Nothing to save — paste some content first.")
        else:
            tags = [t.strip() for t in tags_input.split(",") if t.strip()]
            if storage.file_exists(SHARED_USER, folder, filename):
                st.warning(f"**{filename}** already exists and will be overwritten.")
            with st.spinner("Saving…"):
                try:
                    storage.upload_file(SHARED_USER, folder, filename, pasted.encode("utf-8"), tags, description)
                    st.success(f"✅ **{filename}** saved to **{folder or 'root'}**.")
                except Exception as e:
                    st.error(f"Failed to save: {e}")

    if pasted.strip() and filename:
        st.markdown("")
        st.markdown("**👁️ Preview**")
        with st.container(border=True):
            _render(filename, pasted)

# ===========================================================================
# PAGE: MANAGE FILES
# ===========================================================================

elif page == "manage":
    _page_header("🗂️", "Manage Files", "Edit tags and descriptions, or delete files you no longer need.")

    files = storage.get_all_files()

    if not files:
        st.info("No files stored yet.")
        if st.button("⬆️  Upload your first file", type="primary"):
            _go("upload")
        st.stop()

    grouped: dict[str, list] = {}
    for key, meta in sorted(files.items()):
        folder_name = meta.get("folder") or "(root)"
        grouped.setdefault(folder_name, []).append((key, meta))

    for folder_name, file_list in sorted(grouped.items()):
        st.markdown(f"##### 📂 {folder_name}  <span style='color:#94a3b8;font-size:0.8rem'>({len(file_list)} files)</span>", unsafe_allow_html=True)

        for key, meta in file_list:
            filename  = meta.get("filename", key.split("/")[-1])
            folder    = meta.get("folder", "")
            owner     = meta.get("owner", SHARED_USER)
            tags      = meta.get("tags", [])
            date      = meta.get("uploaded_at", "")[:10]

            with st.container(border=True):
                h1, h2 = st.columns([5, 1])
                with h1:
                    st.markdown(f"**📄 {filename}**")
                    if tags:
                        st.markdown(_pills(tags), unsafe_allow_html=True)
                    st.markdown(f'<div class="file-meta">Uploaded {date}</div>', unsafe_allow_html=True)
                with h2:
                    if st.button("✏️ Edit", key=f"open_{key}", use_container_width=True):
                        st.session_state[f"editing_{key}"] = not st.session_state.get(f"editing_{key}", False)

                if st.session_state.get(f"editing_{key}"):
                    st.divider()
                    with st.form(key=f"form_{key}"):
                        new_tags_input = st.text_input("Tags", value=", ".join(tags))
                        new_desc = st.text_area("Description", value=meta.get("description", ""), height=70)
                        fc1, fc2 = st.columns(2)
                        with fc1:
                            save_btn = st.form_submit_button("💾 Save changes", type="primary", use_container_width=True)
                        with fc2:
                            del_btn = st.form_submit_button("🗑️ Delete file", use_container_width=True)

                    if save_btn:
                        new_tags = [t.strip() for t in new_tags_input.split(",") if t.strip()]
                        with st.spinner("Saving…"):
                            try:
                                storage.update_metadata(owner, folder, filename, new_tags, new_desc)
                                st.success("Updated.")
                                st.session_state[f"editing_{key}"] = False
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

                    if del_btn:
                        st.session_state[f"confirm_{key}"] = True

                if st.session_state.get(f"confirm_{key}"):
                    st.warning(f"⚠️ Are you sure you want to permanently delete **{filename}**?")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        if st.button("Yes, delete", key=f"yes_{key}", type="primary", use_container_width=True):
                            with st.spinner("Deleting…"):
                                try:
                                    storage.delete_file(owner, folder, filename)
                                    for k in [f"confirm_{key}", f"editing_{key}"]:
                                        st.session_state.pop(k, None)
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))
                    with dc2:
                        if st.button("Cancel", key=f"cancel_{key}", use_container_width=True):
                            st.session_state.pop(f"confirm_{key}", None)
                            st.rerun()

        st.markdown("")
