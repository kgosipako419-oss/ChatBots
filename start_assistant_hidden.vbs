' Launch Ekko with NO visible window (runs quietly in the background).
' To stop it later: open Task Manager and end the "python" process,
' or just use start_assistant.bat instead (which you can close).
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\Users\user\Desktop\ChatBots"
sh.Run "cmd /c py -m assistant.main", 0, False
