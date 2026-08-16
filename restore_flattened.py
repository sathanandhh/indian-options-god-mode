from pathlib import Path, PurePosixPath
import re

# ============================================================
# CONFIGURATION
# ============================================================
SOURCE_DIR = Path(__file__).resolve().parent
FLATTENED_FILE = SOURCE_DIR / "flattened_code.txt"

# Matches ONLY the header block itself:
#   ####...####
#   # FILE <n>
#   # PATH: <path>
#   ####...####
#
# IMPORTANT: this does NOT try to also detect where the block ends via a
# lookahead. Each header is located independently with finditer(), and a
# file's content is simply "everything between this header and the start
# of the next one". This is what actually fixes the bug: the old version
# used a single regex with a lookahead for "the next header", and if the
# blank-line spacing between any two blocks didn't match exactly what the
# lookahead expected, that boundary was silently missed — which merges
# many files into one giant "file" and makes most of your files vanish.
# Finding headers independently can't fail that way.
HEADER_PATTERN = re.compile(
    r"#{5,}[ \t]*\n"
    r"#[ \t]*FILE\s+\d+[ \t]*\n"
    r"#[ \t]*PATH:[ \t]*(?P<path>.+?)[ \t]*\n"
    r"#{5,}[ \t]*\n"
)


def normalize_relative_path(raw_path: str) -> Path:
    """
    Convert whatever text was captured after 'PATH:' into a safe,
    OS-correct relative Path.
      - Windows backslashes -> forward slashes (the earlier bug where
        subfolders weren't created on Linux/Mac).
      - Strip leading slashes / stray quotes / whitespace.
    """
    p = raw_path.strip().strip('"').strip("'")
    p = p.replace("\\", "/")
    p = p.lstrip("/")
    parts = [part for part in PurePosixPath(p).parts if part not in ("", ".")]
    return Path(*parts) if parts else Path()


def restore_directory(flattened_file, source_dir, verbose=True):
    flattened_file = Path(flattened_file).resolve()
    source_dir = Path(source_dir).resolve()

    if not flattened_file.exists():
        print("ERROR: Flattened file not found:")
        print(flattened_file)
        return

    content = flattened_file.read_text(encoding="utf-8", errors="ignore")
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    headers = list(HEADER_PATTERN.finditer(content))

    if not headers:
        print("ERROR: No file headers were found.")
        print("Expected header format:")
        print("  ####################")
        print("  # FILE 1")
        print("  # PATH: some/relative/path.py")
        print("  ####################")
        return

    print("=" * 70)
    print("RESTORING PROJECT")
    print("=" * 70)
    print(f"Source directory : {source_dir}")
    print(f"Flattened file   : {flattened_file}")
    print(f"Files detected   : {len(headers)}")
    print("=" * 70)

    restored = 0
    failed = 0

    for i, match in enumerate(headers):
        raw_path = match.group("path")
        content_start = match.end()
        content_end = headers[i + 1].start() if i + 1 < len(headers) else len(content)
        file_content = content[content_start:content_end]

        # Strip exactly the blank-line padding introduced by the header
        # block spacing (one leading newline, trailing blank lines before
        # the next header), without mangling intentional content.
        if file_content.startswith("\n"):
            file_content = file_content[1:]
        file_content = file_content.rstrip("\n")
        if file_content:
            file_content += "\n"

        relative_path = normalize_relative_path(raw_path)

        if verbose:
            print(f"  raw PATH captured: {raw_path!r} -> {relative_path.as_posix()!r}")

        if not relative_path.parts:
            print(f"SKIPPED empty path (raw: {raw_path!r})")
            failed += 1
            continue

        target_file = source_dir / relative_path

        try:
            resolved = target_file.resolve()
            try:
                resolved.relative_to(source_dir)
            except ValueError:
                print(f"SKIPPED unsafe path: {raw_path!r} -> {resolved}")
                failed += 1
                continue

            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(file_content, encoding="utf-8")

            print(f"[OK] {relative_path.as_posix()}")
            restored += 1
        except Exception as e:
            print(f"[ERROR] {raw_path!r} -> {e}")
            failed += 1

    print()
    print("=" * 70)
    print("RESTORE COMPLETED")
    print("=" * 70)
    print(f"Successfully restored : {restored}")
    print(f"Failed                : {failed}")
    print("=" * 70)


if __name__ == "__main__":
    restore_directory(FLATTENED_FILE, SOURCE_DIR)