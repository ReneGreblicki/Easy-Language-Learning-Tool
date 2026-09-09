from __future__ import annotations

from pathlib import Path
from shutil import copyfile
from xml.etree import ElementTree

ANDROID = "http://schemas.android.com/apk/res/android"
ElementTree.register_namespace("android", ANDROID)

REQUIRED_PERMISSIONS = (
    "android.permission.INTERNET",
    "android.permission.ACCESS_NETWORK_STATE",
)
APP_LABEL = "Easy Language Learning Tool"


def configure_manifest(manifest_path: Path, icon_source: Path, icon_target: Path) -> None:
    tree = ElementTree.parse(manifest_path)
    root = tree.getroot()

    existing_permissions = {
        item.get(f"{{{ANDROID}}}name") for item in root.findall("uses-permission")
    }
    for permission in reversed(REQUIRED_PERMISSIONS):
        if permission not in existing_permissions:
            root.insert(
                0,
                ElementTree.Element(
                    "uses-permission",
                    {f"{{{ANDROID}}}name": permission},
                ),
            )

    tts_action = "android.intent.action.TTS_SERVICE"
    query_actions = root.findall("queries/intent/action")
    if not any(item.get(f"{{{ANDROID}}}name") == tts_action for item in query_actions):
        queries = root.find("queries")
        if queries is None:
            queries = ElementTree.Element("queries")
            root.insert(len(root.findall("uses-permission")), queries)
        intent = ElementTree.SubElement(queries, "intent")
        ElementTree.SubElement(
            intent,
            "action",
            {f"{{{ANDROID}}}name": tts_action},
        )

    application = root.find("application")
    if application is None:
        raise RuntimeError("Generated Android manifest has no application element.")
    application.set(f"{{{ANDROID}}}label", APP_LABEL)
    activity = application.find("activity")
    if activity is None:
        raise RuntimeError("Generated Android manifest has no activity element.")

    # Use the same artwork as the Windows and macOS desktop packages.
    icon_target.parent.mkdir(parents=True, exist_ok=True)
    copyfile(icon_source, icon_target)
    application.set(f"{{{ANDROID}}}icon", "@drawable/app_icon")
    application.set(f"{{{ANDROID}}}roundIcon", "@drawable/app_icon")

    scheme = "com.renegreblicki.easylanguageflashcards"
    existing = activity.findall("intent-filter/data")
    if not any(item.get(f"{{{ANDROID}}}scheme") == scheme for item in existing):
        intent_filter = ElementTree.SubElement(activity, "intent-filter")
        ElementTree.SubElement(
            intent_filter,
            "action",
            {f"{{{ANDROID}}}name": "android.intent.action.VIEW"},
        )
        ElementTree.SubElement(
            intent_filter,
            "category",
            {f"{{{ANDROID}}}name": "android.intent.category.DEFAULT"},
        )
        ElementTree.SubElement(
            intent_filter,
            "category",
            {f"{{{ANDROID}}}name": "android.intent.category.BROWSABLE"},
        )
        ElementTree.SubElement(
            intent_filter,
            "data",
            {
                f"{{{ANDROID}}}scheme": scheme,
                f"{{{ANDROID}}}host": "login-callback",
            },
        )

    tree.write(manifest_path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    configure_manifest(
        Path("android/app/src/main/AndroidManifest.xml"),
        Path("../assets/icons/logo.png"),
        Path("android/app/src/main/res/drawable/app_icon.png"),
    )
