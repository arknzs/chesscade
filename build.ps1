$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -c "import sys; assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32, 'Use x64 Python 3.12'"
if ($LASTEXITCODE) { exit $LASTEXITCODE }
if (!(Test-Path 'src/engine/stockfish.exe')) {
    $archive = Join-Path $env:TEMP ('gambit-stockfish-' + [guid]::NewGuid() + '.zip')
    try {
        Invoke-WebRequest 'https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-windows-x86-64-universal.zip' -OutFile $archive
        if ((Get-FileHash $archive).Hash -ne '3C8BF1F9EA66A09350A40DF4F632288285AC206D99F33AB5842C408FC30B48A7') {throw 'Stockfish checksum mismatch'}
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $zip = [IO.Compression.ZipFile]::OpenRead($archive)
        try {
            [IO.Compression.ZipFileExtensions]::ExtractToFile($zip.GetEntry('stockfish/stockfish-windows-x86-64-universal.exe'), (Join-Path $PSScriptRoot 'src/engine/stockfish.exe'))
        } finally {$zip.Dispose()}
    } finally {if (Test-Path $archive) {Remove-Item -LiteralPath $archive}}
}
python -m pip install -r requirements.txt
if ($LASTEXITCODE) { exit $LASTEXITCODE }
$musicArgs = @()
Get-ChildItem -File -Filter 'ambient*.wav' | ForEach-Object {
    $musicArgs += @('--add-data', ($_.Name + ';music'))
}
python -m PyInstaller @musicArgs --noconfirm --clean --onefile --windowed --distpath dist/Gambit67-1.6.10 --name Gambit67 --add-data "src/engine;engine" --icon src/gambit.ico --add-data "src/GambitEncounter.class;." --add-data "src/gambit.ico;." --add-data "licenses;licenses" src/main.py
if ($LASTEXITCODE) { exit $LASTEXITCODE }
python tools/installer.py
exit $LASTEXITCODE

