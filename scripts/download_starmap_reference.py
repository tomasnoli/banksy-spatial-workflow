from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.request import urlopen

UPSTREAM_COMMIT = "9278996c39e376277d57ef95278000447ba6c57c"
URL = (
    f"https://raw.githubusercontent.com/prabhakarlab/Banksy_py/{UPSTREAM_COMMIT}/"
    "data/starmap/starmap_BY3_1k.h5ad"
)
GIT_BLOB_SHA1 = "fbedd8b13083e7b24531c2e374d53033e6f50632"
OUTPUT = Path("data/starmap/starmap_BY3_1k.h5ad")
ANNOTATIONS = "Starmap_BY3_1k_meta_annotated_18oct22.csv"
ANNOTATIONS_SHA1 = "524893f71e77633af31bf333520f98183ec50814"


def git_blob_sha1(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324


def download_verified(url: str, output: Path, expected: str) -> Path:
    if output.exists():
        if git_blob_sha1(output.read_bytes()) != expected:
            raise ValueError(f"Checksum mismatch in existing file: {output}")
        print(f"Verified cached file: {output}")
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}")
    with urlopen(url, timeout=60) as response:  # noqa: S310
        content = response.read()
    digest = git_blob_sha1(content)
    if digest != expected:
        raise ValueError(f"Checksum mismatch: expected {expected}, got {digest}")
    output.write_bytes(content)
    print(f"Saved {output} ({len(content):,} bytes)")
    return output


def main() -> None:
    download_verified(URL, OUTPUT, GIT_BLOB_SHA1)


if __name__ == "__main__":
    main()
