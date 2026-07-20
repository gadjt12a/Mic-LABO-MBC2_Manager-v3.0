; MBC2 Dashboard - Inno Setup installer script
; Build with: BUILD INSTALLER (developer use only).bat
; Paths are relative to this file (windows\); version from VERSION.

#define VerFile FileOpen(SourcePath + "\..\VERSION")
#define AppVer Trim(FileRead(VerFile))
#expr FileClose(VerFile)

[Setup]
AppId={{50CF189E-EBCB-4925-8931-A8FDB9741E3E}
AppName=MBC2 Dashboard
AppVersion={#AppVer}
AppPublisher=mic-LABO Motor Boot Camp 2 Dashboard
DefaultDirName={localappdata}\Programs\MBC2Dashboard
DisableProgramGroupPage=yes
DisableDirPage=yes
; Per-user install - no admin rights needed
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=MBC2Dashboard-Setup-{#AppVer}
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\MBC2Dashboard.exe
Compression=lzma2
SolidCompression=yes
InfoBeforeFile=installer-info.txt
CloseApplications=yes
WizardStyle=modern

[Files]
Source: "..\dist\MBC2Dashboard.exe"; DestDir: "{app}"; Flags: ignoreversion

[Tasks]
Name: desktopicon; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Icons]
Name: "{autodesktop}\MBC2 Dashboard"; Filename: "{app}\MBC2Dashboard.exe"; Tasks: desktopicon
Name: "{autoprograms}\MBC2 Dashboard"; Filename: "{app}\MBC2Dashboard.exe"

[Run]
Filename: "{app}\MBC2Dashboard.exe"; Description: "Launch MBC2 Dashboard"; Flags: nowait postinstall skipifsilent

[Code]
// Ask a running instance to shut down before installing,
// so the exe is never locked mid-update.
function InitializeSetup(): Boolean;
var
  WinHttp: Variant;
begin
  Result := True;
  try
    WinHttp := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    WinHttp.Open('GET', 'http://127.0.0.1:8766/api/shutdown', False);
    WinHttp.SetTimeouts(500, 500, 500, 500);
    WinHttp.Send('');
    Sleep(1500);
  except
    // Not running - nothing to do
  end;
end;

// Remind the user their motor data is untouched after uninstall.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    if not UninstallSilent() then
      MsgBox('Your motor session data has NOT been deleted. It remains in:'#13#10#13#10 +
             ExpandConstant('{localappdata}\MBC2Dashboard'), mbInformation, MB_OK);
end;
