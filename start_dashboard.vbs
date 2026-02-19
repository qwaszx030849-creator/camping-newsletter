Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d C:\Users\PW1234\Desktop" & Chr(32) & Chr(38) Chr(38) & " cd " & Chr(34) & ChrW(50629) & ChrW(47924) & Chr(34) & " & cd camping-newsletter\dashboard & npm run dev", 0, False
