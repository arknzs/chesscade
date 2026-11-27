"""Build the per-user x64 MSI using the Windows Installer API in Python 3.12."""
from pathlib import Path
import msilib as msi
from msilib import schema, sequence

root = Path(__file__).resolve().parents[1]
dist = root / "dist/Chesscade-1.7.0"
db = msi.init_database(str(dist/"Chesscade-Setup.msi"), schema, "Chesscade",
                       "{814C2C20-0DD6-4D24-A0B7-787AC5F199A6}", "1.7.0", "Chesscade")
msi.add_data(db, "Property", [("INSTALLLEVEL","1"), ("ARPNOMODIFY","1"), ("LimitUI","1")])
for table in sequence.tables:
    rows = [row for row in getattr(sequence,table) if row[2] > 0]
    msi.add_data(db,table,rows)
cab = msi.CAB("payload")
directory = msi.Directory(db,cab,None,str(dist),"TARGETDIR","SourceDir")
local = msi.Directory(db,cab,directory,"","LocalAppDataFolder",".")
app = msi.Directory(db,cab,local,"","INSTALLDIR","Chesscade")
menu = msi.Directory(db,cab,directory,"","ProgramMenuFolder",".")
feature = msi.Feature(db,"Game","Chesscade","Chess and arcade encounters",1)
app.start_component("GameFiles",feature,flags=0,keyfile="Chesscade.exe",
                    uuid="{4746AF64-60A4-4957-B665-A479EE1BED9D}")
app.add_file("Chesscade.exe")
app.add_file("Setup-Encounters.ps1",str(root/"tools/Setup-Encounters.ps1"))
app.add_file("README.md",str(root/"README.md"))
brand = msi.Directory(db,cab,app,"src","LogoDirectory","src")
brand.start_component("Logo",feature,flags=0,keyfile="chesscade-logo.png",
                      uuid="{869DA17E-1760-407F-B4FF-1D5F90ED552D}")
brand.add_file("chesscade-logo.png",str(root/"src/chesscade-logo.png"))
app.add_file("COPYING.txt",str(root/"licenses/chess-GPL-3.txt"))
msi.add_data(db,"Shortcut",[("LaunchGame","ProgramMenuFolder","CHESSCAD|Chesscade",
                             "GameFiles","Game",None,None,None,None,None,None,"INSTALLDIR")])
cab.commit(db)
db.Commit()

