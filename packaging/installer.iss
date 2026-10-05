; Inno Setup script for the Windows installer.
; Build:  iscc /DAppVersion=0.1.0 packaging\installer.iss
; Expects the PyInstaller output in dist\ASCII Vision\ (see packaging\ascii-vision.spec).

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{5F0C5B7E-6E1D-4F0B-9A52-3C1B8E7D2A41}
AppName=ASCII Vision
AppVersion={#AppVersion}
AppPublisher=Symmetrical Code
DefaultDirName={autopf}\ASCII Vision
DefaultGroupName=ASCII Vision
UninstallDisplayIcon={app}\ASCII Vision.exe
SetupIconFile=app.ico
OutputDir=..\dist
OutputBaseFilename=ASCII-Vision-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Per-user install by default: no administrator prompt. The user can still pick "all users".
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesEnvironment=yes
LicenseFile=..\LICENSE

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "addtopath"; Description: "Add the ascii-vision command to PATH"; GroupDescription: "Command line:"; Flags: unchecked

[Files]
Source: "..\dist\ASCII Vision\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ASCII Vision"; Filename: "{app}\ASCII Vision.exe"
Name: "{group}\Uninstall ASCII Vision"; Filename: "{uninstallexe}"
Name: "{autodesktop}\ASCII Vision"; Filename: "{app}\ASCII Vision.exe"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "{code:EnvironmentKey}"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}')); Tasks: addtopath

[Run]
Filename: "{app}\ASCII Vision.exe"; Description: "{cm:LaunchProgram,ASCII Vision}"; Flags: nowait postinstall skipifsilent

[Code]
function EnvironmentKey(Param: string): string;
begin
  if IsAdminInstallMode then
    Result := 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
  else
    Result := 'Environment';
end;

function NeedsAddPath(Param: string): Boolean;
var
  OrigPath: string;
  Root: Integer;
begin
  if IsAdminInstallMode then Root := HKEY_LOCAL_MACHINE else Root := HKEY_CURRENT_USER;
  if not RegQueryStringValue(Root, EnvironmentKey(''), 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Uppercase(Param) + ';', ';' + Uppercase(OrigPath) + ';') = 0;
end;
