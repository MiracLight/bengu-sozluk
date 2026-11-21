; Bengü — Inno Setup kurulum betiği
; Derleme:  ISCC.exe /DKaynak=<PyInstaller dist\Bengu klasörü> /DCikti=<çıktı klasörü> paket\bengu.iss

#define Uygulama "Bengü"
#ifndef Surum
  #define Surum "1.0.0"
#endif
#ifndef Kaynak
  #define Kaynak "..\dist\Bengu"
#endif
#ifndef Cikti
  #define Cikti "..\dagitim"
#endif

[Setup]
; AppId sabit kalmalı: sonraki sürümler aynı kimlikle üzerine kurulur (güncelleme)
AppId={{6B3F2A71-8C4D-4E2B-9A57-B3E6D0C1F842}
AppName={#Uygulama}
AppVersion={#Surum}
AppVerName={#Uygulama} {#Surum}
AppPublisher=Bengü
AppComments=Türkçenin Ebedî Sözlüğü
VersionInfoVersion={#Surum}.0
VersionInfoDescription=Bengü — Türkçenin Ebedî Sözlüğü (kurulum)
; Yönetici izni gerekmez; kısa bir yola, kullanıcı hesabına kurulur
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\Bengu
DefaultGroupName={#Uygulama}
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
OutputDir={#Cikti}
OutputBaseFilename=Bengu-Kurulum-{#Surum}
SetupIconFile=bengu.ico
UninstallDisplayIcon={app}\Bengu.exe
UninstallDisplayName={#Uygulama} — Türkçenin Ebedî Sözlüğü
WizardStyle=modern
WizardImageFile=sihirbaz-yan.bmp
WizardSmallImageFile=sihirbaz-kucuk.bmp
InfoBeforeFile=kurulum_bilgi.txt
Compression=lzma2/max
SolidCompression=yes
; Sıkıştırma ayrı (64 bit) süreçte: 32 bit derleyicinin bellek sınırına takılmaz
LZMAUseSeparateProcess=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
; Açık bir Bengü varsa kurulumdan önce kapatılır
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "tr"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "masaustu"; Description: "Masaüstüne Bengü simgesi koy"; GroupDescription: "Kısayollar:"

[Files]
Source: "{#Kaynak}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "kurulum_bilgi.txt"; DestDir: "{app}"; DestName: "BENIOKU.txt"; Flags: ignoreversion

[InstallDelete]
; Eski sürümden kalan uygulama dosyalarını temizle (kullanıcı verisi %LOCALAPPDATA%\Bengu'dadır, dokunulmaz)
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\{#Uygulama}"; Filename: "{app}\Bengu.exe"; Comment: "Türkçenin Ebedî Sözlüğü"
Name: "{group}\Bengü öz testi"; Filename: "{app}\Bengu.exe"; Parameters: "--oztest"; Comment: "Kurulumu sınar ve rapor gösterir"
Name: "{group}\Bengü'yü kaldır"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#Uygulama}"; Filename: "{app}\Bengu.exe"; Tasks: masaustu; Comment: "Türkçenin Ebedî Sözlüğü"

[Run]
Filename: "{app}\Bengu.exe"; Description: "Bengü'yü şimdi başlat"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Açık kalmış Bengü sürecini kapat
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM Bengu.exe"; Flags: runhidden; RunOnceId: "BenguKapat"
