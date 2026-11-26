#!/usr/bin/env python3
"""
project_map.py - Build an AI-friendly overview of a Django / Django REST project.

It walks the project, finds every Python and JavaScript file, and writes a
Markdown file containing:
  * a file tree of all .py / .js files
  * for Python: classes (with base classes), functions and methods with their
    signatures, decorators (e.g. @action, @api_view), first docstring line,
    Django model/serializer fields, key DRF attributes (queryset,
    serializer_class, permission_classes, Meta.model, Meta.fields, ...)
    and URL patterns found in urls.py files
  * for JavaScript: function declarations, arrow functions, classes,
    class/object methods, with parameters and line numbers

Usage:
    python project_map.py                      # scan current dir -> PROJECT_MAP.md
    python project_map.py /path/to/project -o context.md
    python project_map.py --include-migrations --exclude static/vendor
    python project_map.py --js-ext .js .jsx .ts .tsx

Only the standard library is used (Python 3.9+).
"""

import argparse
import ast
import bisect
import re
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", "node_modules", "venv", ".venv", "env",
    "virtualenv", "site-packages", "staticfiles", "dist", "build", "coverage",
    "htmlcov", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".idea",
    ".vscode", "vendor", "bower_components", ".next", ".nuxt",
}
MAX_FILE_BYTES = 1_000_000  # skip huge (usually generated/bundled) files

# ----------------------------------------------------------------------------
# File discovery
# ----------------------------------------------------------------------------

def is_virtualenv(path: Path) -> bool:
    return (path / "pyvenv.cfg").exists()


def looks_minified(path: Path, text: str) -> bool:
    if ".min." in path.name or ".bundle." in path.name:
        return True
    lines = text.splitlines() or [""]
    return sum(len(l) for l in lines) / len(lines) > 300


def collect_files(root: Path, py_ext, js_ext, exclude_dirs, extra_excludes, include_migrations):
    py_files, js_files = [], []
    extra = [Path(e).as_posix().strip("/") for e in extra_excludes]

    def excluded(rel: Path) -> bool:
        rel_s = rel.as_posix()
        return any(rel_s == e or rel_s.startswith(e + "/") for e in extra)

    def walk(directory: Path):
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name.lower())
        except PermissionError:
            return
        for entry in entries:
            rel = entry.relative_to(root)
            if excluded(rel):
                continue
            if entry.is_dir():
                if entry.name in exclude_dirs or entry.name.endswith(".egg-info") or is_virtualenv(entry):
                    continue
                if entry.name == "migrations" and not include_migrations:
                    continue
                walk(entry)
            elif entry.is_file():
                if entry.stat().st_size > MAX_FILE_BYTES:
                    continue
                if entry.suffix in py_ext:
                    py_files.append(entry)
                elif entry.suffix in js_ext:
                    js_files.append(entry)

    walk(root)
    return py_files, js_files


def render_tree(rel_paths):
    tree = {}
    for p in rel_paths:
        node = tree
        for part in p.parts:
            node = node.setdefault(part, {})
    lines = []

    def walk(node, prefix):
        # directories first, then files
        entries = sorted(node.items(), key=lambda kv: (not kv[1], kv[0].lower()))
        for i, (name, child) in enumerate(entries):
            last = i == len(entries) - 1
            lines.append(prefix + ("└── " if last else "├── ") + name + ("/" if child else ""))
            if child:
                walk(child, prefix + ("    " if last else "│   "))

    walk(tree, "")
    return "\n".join(lines)

# ----------------------------------------------------------------------------
# Python parsing (uses the real AST, so it is accurate)
# ----------------------------------------------------------------------------

DRF_ATTRS = {
    "model", "fields", "exclude", "read_only_fields", "extra_kwargs", "depth",
    "queryset", "serializer_class", "permission_classes", "authentication_classes",
    "pagination_class", "filter_backends", "filterset_fields", "filterset_class",
    "search_fields", "ordering_fields", "ordering", "lookup_field", "http_method_names",
    "throttle_classes", "parser_classes", "renderer_classes", "db_table",
    "verbose_name", "unique_together", "abstract", "app_label", "name",
}
URL_FUNCS = {"path", "re_path", "url", "register"}


def short(text: str, limit: int = 100) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def unparse(node) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return "?"


def first_doc_line(node) -> str:
    doc = ast.get_docstring(node)
    if doc and doc.strip():
        return short(doc.strip().splitlines()[0], 120)
    return ""


def call_name(call: ast.Call) -> str:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def class_attributes(cls: ast.ClassDef):
    """Django model/serializer fields and important DRF/Meta attributes."""
    out = []
    for stmt in cls.body:
        target, value = None, None
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            target, value = stmt.targets[0].id, stmt.value
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.value is not None:
            target, value = stmt.target.id, stmt.value
        if target is None:
            continue
        is_field = isinstance(value, ast.Call) and re.search(r"(Field|Key|Serializer)$", call_name(value) or "")
        if is_field or target in DRF_ATTRS:
            out.append(f"{target} = {short(unparse(value))}")
    return out


def parse_python(path: Path, with_docs: bool):
    src = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return None, f"could not parse: {e}"

    items = []

    def visit(body, depth):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kw = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                ret = f" -> {unparse(node.returns)}" if node.returns else ""
                items.append({
                    "depth": depth, "line": node.lineno, "kind": kw,
                    "sig": f"{node.name}({unparse(node.args)}){ret}",
                    "decorators": ["@" + short(unparse(d), 60) for d in node.decorator_list],
                    "doc": first_doc_line(node) if with_docs else "",
                    "attrs": [],
                })
            elif isinstance(node, ast.ClassDef):
                bases = [unparse(b) for b in node.bases]
                items.append({
                    "depth": depth, "line": node.lineno, "kind": "class",
                    "sig": node.name + (f"({', '.join(bases)})" if bases else ""),
                    "decorators": ["@" + short(unparse(d), 60) for d in node.decorator_list],
                    "doc": first_doc_line(node) if with_docs else "",
                    "attrs": class_attributes(node),
                })
                visit(node.body, depth + 1)

    visit(tree.body, 0)

    urls = []
    if path.name == "urls.py" or path.name.endswith("_urls.py"):
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and call_name(node) in URL_FUNCS and node.args:
                args = ", ".join(short(unparse(a), 60) for a in node.args[:2])
                kws = [f"{k.arg}={short(unparse(k.value), 40)}" for k in node.keywords if k.arg in ("name", "basename")]
                urls.append((node.lineno, f"{call_name(node)}({', '.join([args] + kws)})"))
        urls.sort()

    return {"items": items, "urls": urls}, None

# ----------------------------------------------------------------------------
# JavaScript parsing (regex based - good enough for context, not a full parser)
# ----------------------------------------------------------------------------

ID = r"[A-Za-z_$][\w$]*"
FUNC_TAIL = (
    rf"(?P<async>async\s+)?(?:function\b\s*\*?\s*(?:{ID})?\s*\((?P<p1>[^)]*)\)"
    rf"|\((?P<p2>[^)]*)\)\s*=>|(?P<p3>{ID})\s*=>)"
)
RE_FUNC_DECL = re.compile(
    rf"\b(?:export\s+(?:default\s+)?)?(?P<async>async\s+)?function\s*\*?\s*(?P<name>{ID})\s*\((?P<p1>[^)]*)\)"
)
RE_VAR_FUNC = re.compile(rf"\b(?:export\s+)?(?:const|let|var)\s+(?P<name>{ID})\s*=\s*" + FUNC_TAIL)
RE_ASSIGN_FUNC = re.compile(rf"(?P<name>(?:{ID}\.)+{ID})\s*=\s*" + FUNC_TAIL)  # Foo.prototype.bar = ..., module.exports.x = ...
RE_PROP_FUNC = re.compile(rf"(?<![\w$.?])(?P<name>{ID})\s*:\s*" + FUNC_TAIL)  # { name: function() {} } / { name: () => {} }
RE_CLASS = re.compile(rf"\b(?:export\s+(?:default\s+)?)?class\s+(?P<name>{ID})(?:\s+extends\s+(?P<base>[\w$.]+))?")
RE_METHOD = re.compile(
    rf"^[ \t]*(?:static\s+)?(?P<async>async\s+)?(?:get\s+|set\s+)?\*?(?P<name>#?{ID})\s*\((?P<p1>[^)]*)\)\s*\{{",
    re.M,
)
JS_KEYWORDS = {"if", "for", "while", "switch", "catch", "function", "return", "with",
               "else", "do", "try", "typeof", "new", "await", "super", "import"}

RE_JS_TOKENS = re.compile(
    r"""("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`)|(/\*.*?\*/|//[^\n]*)""",
    re.S,
)


def strip_js_comments(src: str) -> str:
    """Blank out comments while keeping strings and line numbers intact."""
    def repl(m):
        if m.group(2):
            return re.sub(r"[^\n]", " ", m.group(2))
        return m.group(0)
    return RE_JS_TOKENS.sub(repl, src)


def parse_js(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    if looks_minified(path, raw):
        return None, "skipped (minified/bundled)"
    src = strip_js_comments(raw)
    newlines = [i for i, c in enumerate(src) if c == "\n"]
    line_of = lambda pos: bisect.bisect_right(newlines, pos) + 1

    found = {}

    def add(pos, kind, name, params="", is_async=False):
        if name in JS_KEYWORDS:
            return
        line = line_of(pos)
        key = (line, name)
        if key in found:
            return
        params = short(params.strip(), 80)
        prefix = "async " if is_async else ""
        found[key] = {"line": line, "kind": kind, "sig": f"{prefix}{name}({params})"}

    def params_of(m):
        return m.group("p1") or m.group("p2") or m.group("p3") or ""

    for m in RE_CLASS.finditer(src):
        line = line_of(m.start())
        sig = m.group("name") + (f" extends {m.group('base')}" if m.group("base") else "")
        found[(line, m.group("name"))] = {"line": line, "kind": "class", "sig": sig}
    for m in RE_FUNC_DECL.finditer(src):
        add(m.start(), "function", m.group("name"), m.group("p1") or "", bool(m.group("async")))
    for m in RE_VAR_FUNC.finditer(src):
        add(m.start(), "function", m.group("name"), params_of(m), bool(m.group("async")))
    for m in RE_ASSIGN_FUNC.finditer(src):
        add(m.start(), "function", m.group("name"), params_of(m), bool(m.group("async")))
    for m in RE_PROP_FUNC.finditer(src):
        add(m.start(), "method", m.group("name"), params_of(m), bool(m.group("async")))
    for m in RE_METHOD.finditer(src):
        add(m.start("name"), "method", m.group("name"), m.group("p1") or "", bool(m.group("async")))

    return sorted(found.values(), key=lambda d: d["line"]), None

# ----------------------------------------------------------------------------
# Markdown output
# ----------------------------------------------------------------------------

def render_python(rel, result):
    out = [f"### `{rel}`"]
    if not result["items"] and not result["urls"]:
        out.append("_(no classes or functions)_")
    for it in result["items"]:
        indent = "  " * it["depth"]
        decos = " ".join(f"`{d}`" for d in it["decorators"])
        line = f"{indent}- {decos + ' ' if decos else ''}**{it['kind']}** `{it['sig']}` (L{it['line']})"
        if it["doc"]:
            line += f" — {it['doc']}"
        out.append(line)
        for a in it["attrs"]:
            out.append(f"{indent}  - `{a}`")
    if result["urls"]:
        out.append("- **URL patterns:**")
        for lineno, u in result["urls"]:
            out.append(f"  - `{u}` (L{lineno})")
    return "\n".join(out)


def render_js(rel, items):
    out = [f"### `{rel}`"]
    if not items:
        out.append("_(no functions found)_")
    for it in items:
        out.append(f"- **{it['kind']}** `{it['sig']}` (L{it['line']})")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Generate an AI-friendly map of a Django/JS project.")
    ap.add_argument("root", nargs="?", default=".", help="project root (default: current directory)")
    ap.add_argument("-o", "--output", default="PROJECT_MAP.md", help="output Markdown file")
    ap.add_argument("--exclude", nargs="*", default=[], help="extra relative paths to skip, e.g. static/vendor")
    ap.add_argument("--include-migrations", action="store_true", help="also scan migrations/ folders")
    ap.add_argument("--no-docs", action="store_true", help="omit docstring summaries")
    ap.add_argument("--no-tree", action="store_true", help="omit the file tree section")
    ap.add_argument("--js-ext", nargs="*", default=[".js", ".jsx", ".mjs", ".cjs"],
                    help="JS-like extensions to scan (add .ts .tsx if you use TypeScript)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        sys.exit(f"Not a directory: {root}")
    output = Path(args.output).resolve()

    py_files, js_files = collect_files(
        root, {".py"}, set(args.js_ext), DEFAULT_EXCLUDE_DIRS, args.exclude, args.include_migrations
    )
    py_files = [p for p in py_files if p.resolve() not in (output, Path(__file__).resolve())]

    py_sections, js_sections, notes = [], [], []
    n_py_funcs = n_js_funcs = 0

    for f in py_files:
        rel = f.relative_to(root).as_posix()
        result, err = parse_python(f, not args.no_docs)
        if err:
            notes.append(f"- `{rel}`: {err}")
            continue
        n_py_funcs += sum(1 for i in result["items"] if i["kind"] != "class")
        py_sections.append(render_python(rel, result))

    for f in js_files:
        rel = f.relative_to(root).as_posix()
        items, err = parse_js(f)
        if err:
            notes.append(f"- `{rel}`: {err}")
            continue
        n_js_funcs += sum(1 for i in items if i["kind"] != "class")
        js_sections.append(render_js(rel, items))

    parts = [
        f"# Project map: {root.name}",
        f"_Generated {datetime.now():%Y-%m-%d %H:%M} by project_map.py. "
        f"{len(py_files)} Python files ({n_py_funcs} functions/methods), "
        f"{len(js_files)} JS files ({n_js_funcs} functions/methods). "
        f"Line numbers are shown as L<n>. Migrations {'included' if args.include_migrations else 'excluded'}._",
    ]
    if not args.no_tree:
        tree = render_tree(sorted(p.relative_to(root) for p in py_files + js_files))
        parts += ["## File tree", f"```text\n{root.name}/\n{tree}\n```"]
    parts += ["## Python", "\n\n".join(py_sections) or "_none found_"]
    parts += ["## JavaScript", "\n\n".join(js_sections) or "_none found_"]
    if notes:
        parts += ["## Skipped / problems", "\n".join(notes)]

    output.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    print(f"  Python: {len(py_files)} files, {n_py_funcs} functions/methods")
    print(f"  JS:     {len(js_files)} files, {n_js_funcs} functions/methods")
    if notes:
        print(f"  {len(notes)} file(s) skipped - see end of the report")


if __name__ == "__main__":
    main()
