#define MyAppName "无尽冬日 MuMu 助手"
#define MyAppVersion "4.1.1"
#define MyAppExeName "WJDRMuMuAssistant.exe"
#define BuildDir "..\..\work\dist_v4_1_1\WJDRMuMuAssistant"

[Setup]
AppId={{6F53579C-9E6F-4C67-98B7-46D65AB38AA4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=WJDR Tools
DefaultDirName={localappdata}\Programs\WJDRMuMuAssistant
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..
OutputBaseFilename=WJDRMuMuAssistant_v4.1.1_Setup
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern dynamic
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
InfoBeforeFile=发行说明.txt
VersionInfoVersion=4.1.1.0
VersionInfoCompany=WJDR Tools
VersionInfoDescription=无尽冬日 MuMu 助手安装程序
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标："; Flags: unchecked

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\全部 MuMu 实例挂机"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--all-auto-help"
Name: "{group}\全部 MuMu 实例抢红包"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--all-auto-red-packet"
Name: "{group}\使用说明"; Filename: "{app}\使用说明.md"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
