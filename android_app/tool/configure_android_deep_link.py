from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

ANDROID = "http://schemas.android.com/apk/res/android"
ElementTree.register_namespace("android", ANDROID)

manifest_path = Path("android/app/src/main/AndroidManifest.xml")
tree = ElementTree.parse(manifest_path)
root = tree.getroot()
application = root.find("application")
if application is None:
    raise RuntimeError("Generated Android manifest has no application element.")
activity = application.find("activity")
if activity is None:
    raise RuntimeError("Generated Android manifest has no activity element.")

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
