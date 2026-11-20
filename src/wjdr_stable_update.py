"""Opt-in portable downloads from this project's explicitly promoted releases."""

from dataclasses import dataclass
import hashlib
import json
import re


REPOSITORY = "eistinlandfrank/wujindongri-mumu-assistant"
LATEST_RELEASE = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
STABLE_LABEL = "WJDR Stable"
VERSION_PATTERN = r"(?:0|[1-9][0-9]{0,4})(?:\.(?:0|[1-9][0-9]{0,4})){2}"
MAX_PORTABLE_BYTES = 512 * 1024 * 1024


@dataclass(frozen=True)
class StableRelease:
    version: str
    filename: str
    url: str
    size: int
    sha256: str


def read_stable_release(payload: bytes, current: str) -> StableRelease | None:
    release = json.loads(payload)
    if not isinstance(release, dict):
        raise ValueError("Invalid GitHub release metadata")
    if release.get("draft") is not False or release.get("prerelease") is not False:
        return None
    tag = release.get("tag_name")
    if not isinstance(tag, str) or not re.fullmatch(f"v{VERSION_PATTERN}", tag):
        return None
    version = tag[1:]
    if tuple(map(int, version.split("."))) <= tuple(map(int, current.split("."))):
        return None

    filename = f"WJDRMuMuAssistant_{tag}_Portable.exe"
    url = f"https://github.com/{REPOSITORY}/releases/download/{tag}/{filename}"
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise ValueError("Invalid GitHub release assets")
    for asset in assets:
        if not isinstance(asset, dict) or asset.get("name") != filename:
            continue
        if asset.get("label") != STABLE_LABEL:
            continue
        digest = asset.get("digest")
        size = asset.get("size")
        if (
            asset.get("state") != "uploaded"
            or asset.get("browser_download_url") != url
            or type(size) is not int
            or not 0 < size <= MAX_PORTABLE_BYTES
            or not isinstance(digest, str)
            or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest)
        ):
            raise ValueError("Invalid stable portable asset")
        return StableRelease(version, filename, url, size, digest[7:].lower())
    return None


class PortableVerification:
    def __init__(self, release: StableRelease) -> None:
        self.release = release
        self.size = 0
        self.digest = hashlib.sha256()

    def add(self, chunk: bytes) -> None:
        self.size += len(chunk)
        if self.size > self.release.size:
            raise ValueError("Unexpected portable size")
        self.digest.update(chunk)

    def complete(self) -> bool:
        return self.size == self.release.size and self.digest.hexdigest() == self.release.sha256
