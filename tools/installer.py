"""Build the per-user x64 MSI using the Windows Installer API in Python 3.12."""
from pathlib import Path
import msilib as msi
from msilib import schema, sequence

root = Path(__file__).resolve().parents[1]
dist = root / "dist/Gambit67-1.6.2"
db = msi.init_database(str(dist/"Gambit67-Setup.msi"), schema, "Gambit 67",
                       "{D4A1B019-E882-4E09-8207-CF2523F9EE7D}", "1.6.2", "Gambit 67")
msi.add_data(db, "Property", [("INSTALLLEVEL","1"), ("ARPNOMODIFY","1"), ("LimitUI","1")])
for table in sequence.tables:
    rows = [row for row in getattr(sequence,table) if row[2] > 0]
    msi.add_data(db,table,rows)
cab = msi.CAB("payload")
directory = msi.Directory(db,cab,None,str(dist),"TARGETDIR","SourceDir")
local = msi.Directory(db,cab,directory,"","LocalAppDataFolder",".")
app = msi.Directory(db,cab,local,"","INSTALLDIR","Gambit67")
menu = msi.Directory(db,cab,directory,"","ProgramMenuFolder",".")
feature = msi.Feature(db,"Game","Gambit 67","Chess and arcade encounters",1)
app.start_component("GameFiles",feature,flags=0,keyfile="Gambit67.exe",
                    uuid="{38695CD4-EE43-45A7-893B-E9D1AD184ECA}")
app.add_file("Gambit67.exe")
app.add_file("Setup-Encounters.ps1",str(root/"tools/Setup-Encounters.ps1"))
app.add_file("README.md",str(root/"README.md"))
app.add_file("COPYING.txt",str(root/"licenses/chess-GPL-3.txt"))
msi.add_data(db,"Shortcut",[("LaunchGame","ProgramMenuFolder","GAMBIT67|Gambit 67",
                             "GameFiles","Game",None,None,None,None,None,None,"INSTALLDIR")])
cab.commit(db)
db.Commit()

