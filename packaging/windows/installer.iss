#ifndef AppVersion
#define AppVersion "0.5.0"
#endif
[Setup]
AppId={{9B923B36-F8D4-45ED-B705-F69010832A9D}
AppName=AI Event Editor
AppVersion={#AppVersion}
AppPublisher=AI Event Editor Project
DefaultDirName={localappdata}\Programs\AI Event Editor
DefaultGroupName=AI Event Editor
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist\installer
OutputBaseFilename=AI-Event-Editor-AI-Setup-{#AppVersion}-Windows-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\AIEventEngine.exe
DisableProgramGroupPage=yes
[Files]
Source: "..\..\dist\AIEventEngine\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\AI Event Editor Setup and Status"; Filename: "{app}\AIEventEngine.exe"
Name: "{group}\Install Premiere panel"; Filename: "{app}\AIEventEditor-Premiere.ccx"
Name: "{group}\Installation guide"; Filename: "{app}\INSTALL_README.txt"
Name: "{group}\Uninstall AI Event Editor"; Filename: "{uninstallexe}"
[Run]
Filename: "{app}\AIEventEngine.exe"; Description: "Finish setup and install the Premiere panel"; Flags: nowait postinstall skipifsilent
