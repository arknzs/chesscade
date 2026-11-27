from pathlib import Path
import subprocess
import tempfile
import textwrap
import zipfile


def launch(java, project, seed, boss=None):
    """Use URL-encoded class paths so Java can load installations in Cyrillic folders."""
    paths = [project/"build/classes/java/main", project/"build/resources/main"]
    urls = [p.resolve().as_uri()+"/" for p in paths]
    urls.extend(p.resolve().as_uri() for p in sorted((project/"libs").glob("*.jar")))
    attribute = "Class-Path: " + " ".join(urls)
    lines = [attribute[:68]] + [" "+part for part in textwrap.wrap(
        attribute[68:], width=67, drop_whitespace=False, break_on_hyphens=False)]
    manifest = "\r\n".join(["Manifest-Version: 1.0", "Main-Class: ChesscadeEncounter", *lines, "", ""])
    folder = tempfile.TemporaryDirectory(prefix="chesscade-")
    try:
        with zipfile.ZipFile(Path(folder.name)/"encounter.jar","w") as jar:
            jar.write(Path(__file__).with_name("ChesscadeEncounter.class"),"ChesscadeEncounter.class")
            jar.writestr("META-INF/MANIFEST.MF",manifest)
        proc = subprocess.Popen([java,"-jar","encounter.jar",str(seed)]+([boss] if boss else []),cwd=folder.name,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        return proc,folder
    except Exception:
        folder.cleanup()
        raise
