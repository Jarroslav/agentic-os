: << 'BATCH_ONLY'
@echo off
REM  run-hook.cmd — one dispatcher that works from both cmd.exe and a shell.
REM
REM  Why a polyglot: the hook scripts are stored without a .sh suffix (plain
REM  "sdlc-stage-guard", "ticket-sync"). That keeps Claude Code's Windows shim
REM  from auto-prefixing "bash" whenever it spots ".sh" in a command line. The
REM  cost is that Windows needs an explicit launcher, which is what this file's
REM  batch half provides; on Unix the leading ":" makes the batch half a no-op
REM  and the shell falls through to the POSIX half at the bottom.
REM
REM  Call as:  run-hook.cmd <hook-name> [extra args...]

REM  First positional arg is the hook to run; bail if it is absent.
if "%~1"=="" (
    echo run-hook.cmd: no hook name given >&2
    exit /b 1
)

REM  Directory this launcher lives in (hooks are siblings of it).
set "HOOKS_HOME=%~dp0"

REM  Preferred: the bash that ships with Git for Windows.
for %%B in (
    "C:\Program Files\Git\bin\bash.exe"
    "C:\Program Files (x86)\Git\bin\bash.exe"
) do (
    if exist %%~B (
        %%~B "%HOOKS_HOME%%~1" %2 %3 %4 %5 %6 %7 %8 %9
        exit /b %ERRORLEVEL%
    )
)

REM  Otherwise fall back to whatever bash is on PATH (MSYS2, Cygwin, etc.).
where bash >nul 2>nul && (
    bash "%HOOKS_HOME%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

REM  No bash at all: treat hooks as a no-op so the plugin still loads.
exit /b 0
BATCH_ONLY

# POSIX path: dispatch the requested hook from this file's own directory.
here="$(cd "$(dirname "$0")" && pwd)"
hook="$1"
shift
exec bash "${here}/${hook}" "$@"
