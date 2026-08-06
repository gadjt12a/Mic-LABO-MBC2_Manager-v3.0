; MBC2 Dashboard - Inno Setup installer script
; Build with: BUILD INSTALLER (developer use only).bat
; Paths are relative to this file (windows\); version from VERSION.

#define VerFile FileOpen(SourcePath + "\..\app\VERSION")
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
SetupIconFile=..\app\icon.ico
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
// True while any MBC2Dashboard.exe process still exists.
function AppStillRunning(): Boolean;
var
  Locator, Service, Procs: Variant;
begin
  Result := False;
  try
    Locator := CreateOleObject('WbemScripting.SWbemLocator');
    Service := Locator.ConnectServer('.', 'root\CIMV2');
    Procs := Service.ExecQuery(
      'SELECT ProcessId FROM Win32_Process WHERE Name = "MBC2Dashboard.exe"');
    Result := Procs.Count > 0;
  except
    // If WMI is unavailable we cannot tell - assume clear and let Restart
    // Manager have its usual go at it.
  end;
end;

// Ask a running instance to shut down before installing,
// so the exe is never locked mid-update.
function InitializeSetup(): Boolean;
var
  WinHttp: Variant;
  Waited: Integer;
begin
  Result := True;
  try
    WinHttp := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    WinHttp.Open('GET', 'http://127.0.0.1:8766/api/shutdown', False);
    WinHttp.SetTimeouts(2000, 2000, 2000, 2000);
    WinHttp.Send('');
  except
    // Not running - nothing to do
  end;

  // The server releases port 8766 at once, but the PyInstaller onefile
  // bootloader parent outlives it by ~5s and keeps MBC2Dashboard.exe locked.
  // Restart Manager cannot close that process - it has no message loop - so a
  // fixed short sleep here left setup aborting with "Setup was unable to
  // automatically close all applications" (exit code 5) whenever the app was
  // open, which is the ordinary upgrade path. Wait for the process to actually
  // go, then give the filesystem a moment to release the handle.
  Waited := 0;
  while AppStillRunning() and (Waited < 20000) do
  begin
    Sleep(500);
    Waited := Waited + 500;
  end;
  Sleep(500);
end;

// Remind the user their motor data is untouched after uninstall.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    if not UninstallSilent() then
      MsgBox('Your motor session data has NOT been deleted. It remains in:'#13#10#13#10 +
             ExpandConstant('{localappdata}\MBC2Dashboard'), mbInformation, MB_OK);
end;
