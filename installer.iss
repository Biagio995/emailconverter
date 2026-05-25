; Inno Setup — pacchetto di installazione unico per MBOX to PDF
; Compila con: iscc installer.iss
; Oppure: python build_exe.py (include anche l'installer se Inno Setup è installato)

#define MyAppName "MBOX to PDF"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MBOX to PDF"
#define MyAppExeName "MBOXtoPDF.exe"
#define SourceDir "dist\MBOXtoPDF"

[Setup]
AppId={{8E4A1F92-6C3D-4B8E-9A1F-2D7E5B4C9A30}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=MBOXtoPDF_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=
LicenseFile=
InfoBeforeFile=

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Avvia {#MyAppName}"; Flags: nowait postinstall skipifsilent
