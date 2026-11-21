# Bengü — baştan sona derleme: veri → vektör dizini → testler → Bengu.exe → Bengu-Kurulum-<sürüm>.exe
#
# Kullanım (bengu klasöründe):
#   powershell -ExecutionPolicy Bypass -File paket\derle.ps1                 # her şeyi yeniden kur
#   powershell -ExecutionPolicy Bypass -File paket\derle.ps1 -VeriAtla       # veritabanı hazırsa yalnız paketle
#
# Gerekenler: Python 3.12+, Inno Setup 6. Python paketleri ilk çalıştırmada kısa yollu bir sanal ortama kurulur.
# Windows'un 260 karakter yol sınırına takılmamak için derleme %TEMP%\bengu-derleme altında yapılır.
param([switch]$VeriAtla, [string]$Python = "python")

$ErrorActionPreference = "Stop"
$Kok = Split-Path -Parent $PSScriptRoot
$Gecici = Join-Path $env:TEMP "bengu-derleme"
$Venv = Join-Path $Gecici "venv"
$Surum = (Select-String -Path "$Kok\surum.py" -Pattern 'SURUM = "(.+)"').Matches[0].Groups[1].Value
Write-Host "Bengü $Surum derleniyor…" -ForegroundColor Yellow

if (-not (Test-Path "$Venv\Scripts\python.exe")) {
    & $Python -m venv $Venv
    & "$Venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r "$Kok\gereksinimler.txt" pyinstaller
}
$Py = "$Venv\Scripts\python.exe"

Push-Location $Kok
try {
    if (-not $VeriAtla) {
        & $Py araclar\aktar.py;  if ($LASTEXITCODE) { throw "Veri aktarımı başarısız" }
        & $Py araclar\vektor.py; if ($LASTEXITCODE) { throw "Vektör dizini başarısız" }
    }
    & $Py testler\rehber_testi.py; if ($LASTEXITCODE) { throw "Rehber testi başarısız: paket üretilmedi" }

    & $Py -m PyInstaller paket\bengu.spec --noconfirm --clean --distpath "$Gecici\dist" --workpath "$Gecici\work"
    if ($LASTEXITCODE) { throw "PyInstaller başarısız" }

    $oz = Start-Process "$Gecici\dist\Bengu\Bengu.exe" -ArgumentList "--oztest", "--sessiz" -Wait -PassThru
    if ($oz.ExitCode) { throw "Derlenmiş uygulamanın öz testi başarısız: $env:LOCALAPPDATA\Bengu\oztest.txt" }

    $Iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
              "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $Iscc) { throw "Inno Setup 6 bulunamadı (https://jrsoftware.org/isdl.php)" }
    New-Item -ItemType Directory -Force "$Kok\dagitim" | Out-Null
    Push-Location "$Kok\paket"
    & $Iscc /Q "/DKaynak=$Gecici\dist\Bengu" "/DCikti=$Gecici\kurulum" "/DSurum=$Surum" bengu.iss
    Pop-Location
    if ($LASTEXITCODE) { throw "Inno Setup başarısız" }
    Copy-Item "$Gecici\kurulum\Bengu-Kurulum-$Surum.exe" "$Kok\dagitim\" -Force
    $boyut = [math]::Round((Get-Item "$Kok\dagitim\Bengu-Kurulum-$Surum.exe").Length / 1MB, 1)
    Write-Host "Hazır: dagitim\Bengu-Kurulum-$Surum.exe ($boyut MB)" -ForegroundColor Green
}
finally { Pop-Location }
