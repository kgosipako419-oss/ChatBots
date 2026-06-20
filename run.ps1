# Convenience launcher. Usage:
#   .\run.ps1          -> voice mode
#   .\run.ps1 text     -> text REPL
#   .\run.ps1 check    -> check Ollama/config
param([string]$mode = "voice")

switch ($mode) {
    "text"   { py -m assistant.main --text }
    "check"  { py -m assistant.main --check }
    "audio"  { py -m assistant.main --list-audio }
    "voices" { py -m assistant.main --list-voices }
    default  { py -m assistant.main }
}
