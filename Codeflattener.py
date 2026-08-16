from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

SOURCE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = SOURCE_DIR / "flattened_code.txt"

EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", ".venv", "venv", "env",
    "node_modules", ".idea", ".vscode", "dist", "build", "target",
    ".pytest_cache", ".mypy_cache",
}

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".go", ".rs", ".php", ".rb", ".swift", ".kt", ".kts", ".sql",
    ".html", ".htm", ".css", ".scss", ".sass", ".less", ".xml", ".json",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".md", ".txt",
    ".sh", ".bat", ".ps1", ".dockerfile",
}

SPECIAL_FILES = {
    "dockerfile", "makefile", "requirements.txt", "pyproject.toml",
    "package.json", "package-lock.json", "docker-compose.yml",
    "docker-compose.yaml", ".env.example",
}

def should_include(file_path):
    if file_path.resolve() == OUTPUT_FILE.resolve():
        return False
    if any(part in EXCLUDED_DIRS for part in file_path.parts):
        return False
    if file_path.name.lower() in {x.lower() for x in SPECIAL_FILES}:
        return True
    return file_path.suffix.lower() in CODE_EXTENSIONS

def flatten_directory(source_dir, output_file):
    source_dir = Path(source_dir).resolve()
    output_file = Path(output_file).resolve()
    files = []
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        if should_include(path):
            files.append(path)
    files.sort(key=lambda x: str(x.relative_to(source_dir)).lower())

    with open(output_file, "w", encoding="utf-8", errors="ignore") as output:
        output.write("=" * 100 + "\n")
        output.write("FLATTENED PROJECT SOURCE CODE\n")
        output.write("=" * 100 + "\n\n")
        output.write(f"Project: {source_dir.name}\n")
        output.write(f"Source: {source_dir}\n")
        output.write(f"Files included: {len(files)}\n\n")
        output.write("=" * 100 + "\n")

        for index, file_path in enumerate(files, start=1):
            relative_path = file_path.relative_to(source_dir)
            output.write("\n\n")
            output.write("#" * 100 + "\n")
            output.write(f"# FILE {index}\n")
            output.write(f"# PATH: {relative_path}\n")
            output.write("#" * 100 + "\n\n")
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                output.write(content)
                if not content.endswith("\n"):
                    output.write("\n")
            except Exception as e:
                output.write(f"\n[ERROR READING FILE: {e}]\n")

if __name__ == "__main__":
    flatten_directory(SOURCE_DIR, OUTPUT_FILE)

