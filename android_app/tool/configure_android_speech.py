import re
from pathlib import Path


def configure_speech(android_main: Path, template: Path) -> None:
    activities = list(android_main.rglob("MainActivity.kt"))
    if len(activities) != 1:
        raise RuntimeError("Expected exactly one generated Kotlin MainActivity.")
    activity = activities[0]
    content = activity.read_text(encoding="utf-8")
    package = re.search(r"^package\s+([\w.]+)", content, re.MULTILINE)
    if package is None:
        raise RuntimeError("MainActivity package was missing.")
    if "AppSpeechPlugin" not in content:
        if not re.search(r"class MainActivity\s*:\s*FlutterActivity\(\)\s*$", content):
            raise RuntimeError(
                "MainActivity differs from the generated template; review registration."
            )
        content = re.sub(
            r"class MainActivity\s*:\s*FlutterActivity\(\)\s*$",
            "class MainActivity : FlutterActivity() {\n"
            "    override fun configureFlutterEngine(flutterEngine: io.flutter.embedding.engine.FlutterEngine) {\n"
            "        super.configureFlutterEngine(flutterEngine)\n"
            "        flutterEngine.plugins.add(AppSpeechPlugin())\n"
            "    }\n}\n",
            content,
        )
        activity.write_text(content, encoding="utf-8")
    (activity.parent / "AppSpeechPlugin.kt").write_text(
        template.read_text(encoding="utf-8").replace("__APP_PACKAGE__", package.group(1)),
        encoding="utf-8",
    )


if __name__ == "__main__":
    configure_speech(Path("android/app/src/main"), Path("tool/native/AppSpeechPlugin.kt"))
