; Inno Setup script: wraps the PyInstaller build in a Windows installer.
;
;     uv run pyinstaller packaging/printpicker.spec --noconfirm
;     iscc /DAppVersion=1.2.3 packaging/windows/printpicker.iss
;
; Output: out/PrintPicker-windows-x64-setup.exe. Installs for the current user (no admin needed);
; the setup offers an all-users install too.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\dist\PrintPicker"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\out"
#endif

#define AppName "PrintPicker"
#define AppExe "PrintPicker.exe"
#define RepoUrl "https://github.com/GiacomoGuaresi/PrintPicker"

[Setup]
; Never change AppId: it is how Windows recognises an update of an installed PrintPicker.
AppId={{7E2C4B1A-3F5D-4C8E-9A61-2B7D0F4E8C35}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Giacomo Guaresi
AppPublisherURL={#RepoUrl}
AppSupportURL={#RepoUrl}/issues
AppUpdatesURL={#RepoUrl}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\..\LICENSE
SetupIconFile=..\icons\printpicker.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
OutputDir={#OutputDir}
OutputBaseFilename=PrintPicker-windows-x64-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; Libraries of the previous version must not mix with the new ones.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
