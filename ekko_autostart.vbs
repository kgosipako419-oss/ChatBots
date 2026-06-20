' Ekko auto-start: launched at Windows logon, runs hidden (no window).
' Logs to ekko.log in the project folder so problems can be diagnosed.
' To disable autostart: delete the "Ekko Assistant" shortcut from the Startup folder
'   (press Win+R, type  shell:startup  , and delete it there).
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\Users\user\Desktop\ChatBots"
sh.Run "cmd /c py -u -m assistant.main > ekko.log 2>&1", 0, False
