; Εργαστήρι R2 (R2 Lab) - installer για Windows (Inno Setup 6)
; Τον φτιάχνει το windows\build_exe.bat, που περνά την έκδοση από το core\__init__.py:
;     iscc /DAppVer=1.10.0 windows\r2_lab.iss
; Είσοδος: ..\build\windows\R2Lab\  (το φτιάχνει το PyInstaller)
; Έξοδος:  ..\dist\R2-Lab-Setup-<έκδοση>.exe
; Το αρχείο πρέπει να μένει UTF-8 με BOM, αλλιώς τα ελληνικά βγαίνουν λάθος.
; Το Inno Setup δεν έχει ελληνικά, οπότε τα βήματα του installer είναι στα αγγλικά.

#ifndef AppVer
  #define AppVer "1.10.0"
#endif
#define AppName "Εργαστήρι R2"
#define AppExe "R2Lab.exe"
; Η προηγούμενη έκδοση λεγόταν «Παιχνίδια Μάθησης» (EduGames.exe).
#define OldName "Παιχνίδια Μάθησης"
#define OldExe "EduGames.exe"

[Setup]
; Ίδιο AppId με τα «Παιχνίδια Μάθησης»: ο installer αναβαθμίζει την παλιά εγκατάσταση
; (στον ίδιο φάκελο) αντί να βάλει δεύτερο πρόγραμμα.
AppId={{212D0711-8D40-444D-84F7-F2C3D3375A1C}
AppName={#AppName}
AppVersion={#AppVer}
AppVerName={#AppName} {#AppVer}
AppPublisher=Χρόνης Τραστόγιαννος
AppContact=ctrastogia@sch.gr
AppComments=Παιχνίδια λογικής, ρομποτικής και μάθησης για μικρά παιδιά, με το ρομπότ R2
DefaultDirName={autopf}\R2 Lab
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=R2-Lab-Setup-{#AppVer}
SetupIconFile=..\assets\r2-lab.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName} {#AppVer}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog commandline
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; Τα εικονίδια και το .exe της παλιάς έκδοσης, για να μη μείνουν δύο εικονίδια.
Type: files; Name: "{app}\{#OldExe}"
Type: files; Name: "{autoprograms}\{#OldName}.lnk"
Type: files; Name: "{autoprograms}\Απεγκατάσταση - {#OldName}.lnk"
Type: files; Name: "{autodesktop}\{#OldName}.lnk"

[Files]
Source: "..\build\windows\R2Lab\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autoprograms}\Απεγκατάσταση - {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; Ποδόσφαιρο στο δίκτυο: άδεια στο τείχος προστασίας των Windows για τον υπολογιστή που «φτιάχνει γήπεδο»,
; για να μη ρωτάει τα παιδιά. Πρώτα σβήνει τον κανόνα μιας παλιότερης εγκατάστασης.
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""R2 Lab"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""R2 Lab"" dir=in action=allow program=""{app}\{#AppExe}"" enable=yes profile=any"; Flags: runhidden waituntilterminated
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""R2 Lab"""; Flags: runhidden waituntilterminated; RunOnceId: "DelFirewallRule"
