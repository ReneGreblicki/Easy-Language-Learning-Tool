from __future__ import annotations

import argparse
import json
import plistlib
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

APP_LABEL = "Easy Language Learning Tool"
BUNDLE_ID = "com.renegreblicki.easylanguagelearningtool"
CALLBACK_SCHEME = "com.renegreblicki.easylanguageflashcards"
MINIMUM_IOS_VERSION = "13.0"


def configure_info_plist(plist_path: Path) -> None:
    with plist_path.open("rb") as handle:
        payload = plistlib.load(handle)
    payload["CFBundleDisplayName"] = APP_LABEL
    payload["CFBundleName"] = APP_LABEL
    payload["ITSAppUsesNonExemptEncryption"] = False
    url_types = payload.setdefault("CFBundleURLTypes", [])
    if not any(CALLBACK_SCHEME in item.get("CFBundleURLSchemes", []) for item in url_types):
        url_types.append(
            {
                "CFBundleTypeRole": "Editor",
                "CFBundleURLName": BUNDLE_ID,
                "CFBundleURLSchemes": [CALLBACK_SCHEME],
            }
        )
    with plist_path.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=False)


def configure_xcode_project(
    project_path: Path,
    team_id: str = "",
    profile_name: str = "",
) -> None:
    text = project_path.read_text(encoding="utf-8")
    text = re.sub(
        r"IPHONEOS_DEPLOYMENT_TARGET = [^;]+;",
        f"IPHONEOS_DEPLOYMENT_TARGET = {MINIMUM_IOS_VERSION};",
        text,
    )

    def replace_bundle(match: re.Match[str]) -> str:
        old_identifier = match.group(1)
        suffix = ".RunnerTests" if old_identifier.endswith(".RunnerTests") else ""
        return f"PRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID}{suffix};"

    text = re.sub(r"PRODUCT_BUNDLE_IDENTIFIER = ([^;]+);", replace_bundle, text)
    if team_id:
        if "DEVELOPMENT_TEAM =" in text:
            text = re.sub(r"DEVELOPMENT_TEAM = [^;]*;", f"DEVELOPMENT_TEAM = {team_id};", text)
        else:
            text = text.replace(
                "CODE_SIGN_STYLE = Automatic;",
                f"CODE_SIGN_STYLE = Automatic;\n\t\t\t\tDEVELOPMENT_TEAM = {team_id};",
            )
    if profile_name:
        text = text.replace("CODE_SIGN_STYLE = Automatic;", "CODE_SIGN_STYLE = Manual;")
        if "PROVISIONING_PROFILE_SPECIFIER =" in text:
            text = re.sub(
                r"(PROVISIONING_PROFILE_SPECIFIER(?:\[[^\]]+\])? = )[^;]*;",
                rf'\1"{profile_name}";',
                text,
            )
        else:
            text = text.replace(
                "CODE_SIGN_STYLE = Manual;",
                "CODE_SIGN_STYLE = Manual;\n"
                f'\t\t\t\tPROVISIONING_PROFILE_SPECIFIER = "{profile_name}";',
            )
        if "CODE_SIGN_IDENTITY" in text:
            text = re.sub(
                r"(CODE_SIGN_IDENTITY(?:\[[^\]]+\])? = )[^;]*;",
                r'\1"Apple Distribution";',
                text,
            )
        else:
            text = text.replace(
                "CODE_SIGN_STYLE = Manual;",
                'CODE_SIGN_STYLE = Manual;\n\t\t\t\tCODE_SIGN_IDENTITY = "Apple Distribution";',
            )
    project_path.write_text(text, encoding="utf-8")


def write_export_options(path: Path, team_id: str, profile_name: str) -> None:
    payload = {
        "destination": "export",
        "manageAppVersionAndBuildNumber": False,
        "method": "app-store-connect",
        "provisioningProfiles": {BUNDLE_ID: profile_name},
        "signingStyle": "manual",
        "stripSwiftSymbols": True,
        "teamID": team_id,
        "uploadBitcode": False,
        "uploadSymbols": True,
    }
    with path.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=False)


def configure_podfile(podfile_path: Path) -> None:
    text = podfile_path.read_text(encoding="utf-8")
    replacement = f"platform :ios, '{MINIMUM_IOS_VERSION}'"
    if re.search(r"^#?\s*platform :ios,", text, flags=re.MULTILINE):
        text = re.sub(
            r"^#?\s*platform :ios,.*$",
            replacement,
            text,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        text = replacement + "\n\n" + text
    podfile_path.write_text(text, encoding="utf-8")


def install_icons(
    icon_source: Path,
    appicon_directory: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    catalog = json.loads((appicon_directory / "Contents.json").read_text(encoding="utf-8"))
    generated: set[tuple[str, int]] = set()
    for image in catalog.get("images", []):
        filename = image.get("filename")
        size = image.get("size")
        scale = image.get("scale")
        if not filename or not size or not scale:
            continue
        points = float(size.split("x", maxsplit=1)[0])
        pixels = round(points * float(scale.rstrip("x")))
        key = (filename, pixels)
        if key in generated:
            continue
        generated.add(key)
        runner(
            [
                "sips",
                "-z",
                str(pixels),
                str(pixels),
                str(icon_source),
                "--out",
                str(appicon_directory / filename),
            ],
            check=True,
            capture_output=True,
            text=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--team-id", default="")
    parser.add_argument("--profile-name", default="")
    parser.add_argument("--export-options", default="")
    args = parser.parse_args()
    team_id = args.team_id.strip()
    profile_name = args.profile_name.strip()
    configure_info_plist(Path("ios/Runner/Info.plist"))
    configure_xcode_project(
        Path("ios/Runner.xcodeproj/project.pbxproj"),
        team_id=team_id,
        profile_name=profile_name,
    )
    configure_podfile(Path("ios/Podfile"))
    install_icons(
        Path("../assets/icons/logo.png"),
        Path("ios/Runner/Assets.xcassets/AppIcon.appiconset"),
    )
    if args.export_options:
        if not team_id or not profile_name:
            parser.error("--export-options requires --team-id and --profile-name")
        write_export_options(Path(args.export_options), team_id, profile_name)


if __name__ == "__main__":
    main()
