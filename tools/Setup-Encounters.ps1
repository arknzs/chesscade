$ErrorActionPreference = 'Stop'
$compiler = Get-Command javac -ErrorAction SilentlyContinue
if (!$compiler) {throw 'Install JDK 21+ and add javac to PATH.'}
$repo = Join-Path $env:LOCALAPPDATA 'ChesscadeEncounters'
$source = Join-Path $repo 'upstream'
if (!(Test-Path "$source/.git")) {
    git clone --filter=blob:none --no-checkout https://github.com/ThakornToon/undertale-boss-fight.git $source
    if ($LASTEXITCODE) {throw 'Git clone failed'}
}
git -C $source sparse-checkout set src/main libs
if ($LASTEXITCODE) {throw 'Sparse checkout failed'}
git -C $source checkout 499722735b81b0ea2c8e4586e88d08e4178cc494
if ($LASTEXITCODE) {throw 'Checkout failed'}
$classes = Join-Path $repo 'build/classes/java/main'
$resources = Join-Path $repo 'build/resources/main'
New-Item -Force -ItemType Directory $classes,$resources,"$repo/libs" | Out-Null
Push-Location $source
try {
    $sources = Get-ChildItem src/main/java -Recurse -Filter *.java | ForEach-Object { $_.FullName.Substring($source.Length+1).Replace('\','/') }
    $sources | Set-Content sources-chesscade.txt -Encoding Ascii
    & $compiler.Source -encoding UTF-8 -cp 'libs/*' -d $classes '@sources-chesscade.txt'
    if ($LASTEXITCODE) {throw 'Compilation failed'}
    Copy-Item 'src/main/resources/*' $resources -Recurse -Force
    Copy-Item 'libs/*.jar' "$repo/libs" -Force
} finally {Pop-Location}
