Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 动态获取脚本所在目录，避免编码导致的路径问题
strScriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strScriptPath

' 使用 cmd /c 启动批处理文件并隐藏窗口 (0 代表隐藏)
WshShell.Run "cmd /c run_app.bat", 0

Set fso = Nothing
Set WshShell = Nothing
