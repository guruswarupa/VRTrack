; VRTrack Windows installer (Inno Setup 6).
; Installs the VRTrack desktop app AND OpenTrack, opens the firewall for the phone, and pre-configures OpenTrack.
;
; Build with installer\build.ps1 (it passes AppVersion and the path of the OpenTrack setup).

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef OpenTrackSetup
  #define OpenTrackSetup "build\opentrack-setup.exe"
#endif
#ifndef OpenTrackVersion
  #define OpenTrackVersion "2026.1.0"
#endif

[Setup]
AppId={{B7E3F4A2-5C1D-4E8A-9F36-7A2D1C0E5B94}
AppName=VRTrack
AppVersion={#AppVersion}
AppPublisher=VRTrack
AppPublisherURL=https://github.com/
DefaultDirName={autopf}\VRTrack
DefaultGroupName=VRTrack
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\VRTrack.exe
UninstallDisplayName=VRTrack
SetupIconFile=..\assets\branding\icon.ico
WizardImageFile=..\assets\branding\installer-side.bmp
WizardSmallImageFile=..\assets\branding\installer-small.bmp
WizardStyle=modern
OutputDir=build\out
OutputBaseFilename=VRTrack-Setup-{#AppVersion}
Compression=lzma2/fast
SolidCompression=no
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "Start VRTrack when I sign in to Windows"; GroupDescription: "Options:"; Flags: unchecked

[Files]
Source: "build\dist\VRTrack\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion
; Official OpenTrack installer, unmodified; only extracted when OpenTrack is not installed yet.
Source: "{#OpenTrackSetup}"; DestDir: "{tmp}"; DestName: "opentrack-setup.exe"; Flags: deleteafterinstall; Check: NeedOpenTrack

[Icons]
Name: "{autoprograms}\VRTrack"; Filename: "{app}\VRTrack.exe"
Name: "{autodesktop}\VRTrack"; Filename: "{app}\VRTrack.exe"; Tasks: desktopicon
Name: "{userstartup}\VRTrack"; Filename: "{app}\VRTrack.exe"; Parameters: "--minimized"; Tasks: startup

[Run]
; 1. OpenTrack (silent, official installer)
Filename: "{tmp}\opentrack-setup.exe"; Parameters: "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-"; \
  StatusMsg: "Installing OpenTrack {#OpenTrackVersion} (about a minute)..."; Flags: waituntilterminated; Check: NeedOpenTrack
; 2. Firewall: let the phone reach VRTrack. Any network profile (USB tethering is often "Public"), but only
;    from the local subnet, so nothing outside your LAN can reach it.
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""VRTrack"""; Flags: runhidden; StatusMsg: "Configuring firewall..."
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""VRTrack"" dir=in action=allow program=""{app}\VRTrack.exe"" protocol=UDP remoteip=localsubnet profile=any enable=yes"; Flags: runhidden
; 3. Launch
Filename: "{app}\VRTrack.exe"; Description: "Launch VRTrack"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""VRTrack"""; Flags: runhidden; RunOnceId: "DelFirewall"

[Code]
function OpenTrackInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{commonpf32}\opentrack\opentrack.exe'))
         or FileExists(ExpandConstant('{commonpf}\opentrack\opentrack.exe'));
end;

function NeedOpenTrack: Boolean;
begin
  Result := not OpenTrackInstalled;
end;

function OpenTrackProfile: String;
begin
  { UDP over network -> freetrack 2.0 Enhanced, EWMA filter (VRTrack already smooths and interpolates). }
  Result :=
    '[migrations]' + #13#10 +
    'last-migration-at=20220126_00~' + #13#10 + #13#10 +
    '[modules]' + #13#10 +
    'tracker-dll=udp' + #13#10 +
    'protocol-dll=freetrack' + #13#10 +
    'filter-dll=ewma' + #13#10;
end;

procedure ConfigureOpenTrack;
var
  Dir, DefaultIni: String;
  Existing: AnsiString;
begin
  Dir := ExpandConstant('{userdocs}\opentrack-2.3');
  ForceDirectories(Dir);
  { Always provide a ready-made profile. }
  SaveStringToFile(Dir + '\VRTrack.ini', OpenTrackProfile, False);
  { Make it the active profile only if the user has not configured OpenTrack themselves. }
  DefaultIni := Dir + '\default.ini';
  if (not FileExists(DefaultIni)) or
     (LoadStringFromFile(DefaultIni, Existing) and (Pos('tracker-dll=', String(Existing)) = 0)) then
    SaveStringToFile(DefaultIni, OpenTrackProfile, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    ConfigureOpenTrack;
end;

function InitializeSetup: Boolean;
begin
  Result := True;
end;
