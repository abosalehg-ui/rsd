; ╔══════════════════════════════════════════════════════════════╗
; ║   رصد (Rasad) — سكربت Inno Setup لبناء مثبّت ويندوز كامل        ║
; ╚══════════════════════════════════════════════════════════════╝
;
; يلتقط مُخرَج PyInstaller (dist\rasad\) ويبني مثبّتاً واحداً مع اختصارات
; وأيقونة وأداة إزالة. ابنِ التطبيق أولاً عبر packaging\build_installer.bat
; أو يدوياً (راجع packaging\README.md)، ثم صرّف هذا الملف بـ Inno Setup 6.

#define MyAppName "رصد Rasad"
#define MyAppVersion "1.5.0"
#define MyAppPublisher "عبدالكريم العبود"
#define MyAppURL "https://github.com/abosalehg-ui/rsd"
#define MyAppExeName "rasad.exe"

[Setup]
AppId={{533DEC10-7A04-4656-9D0C-7B3D2427B603}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\Rasad
DefaultGroupName=Rasad
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=Rasad-Setup-x64
SetupIconFile=rasad.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
; الإنجليزية مضمونة دائماً مع Inno Setup. لإضافة واجهة معالِج عربية:
; نزّل Arabic.isl إلى مجلّد Languages لدى Inno Setup ثم أزل التعليق عن السطر التالي.
Name: "english"; MessagesFile: "compiler:Default.isl"
; Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; كامل مجلّد onedir الناتج عن PyInstaller
Source: "..\dist\rasad\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; الأيقونة (لاختصارات القائمة/سطح المكتب)
Source: "rasad.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\rasad.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\rasad.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
