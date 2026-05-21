[CmdletBinding()]
param(
    [string]$Version = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$File,
            [AllowEmptyCollection()][string[]]$Args = @()
    )

    & $File @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed (exit $LASTEXITCODE): $File $($Args -join ' ')"
    }
}

function Test-PythonVersion {
    param(
        [Parameter(Mandatory = $true)][string]$File,
        [AllowEmptyCollection()][string[]]$Args = @()
    )

    try {
        $output = & $File @Args '-c' 'import sys; print("{}.{}".format(sys.version_info.major, sys.version_info.minor))' 2>$null
        if ($LASTEXITCODE -eq 0 -and $output -eq '3.12') {
            return $true
        }
    } catch {
        # ignore
    }
    return $false
}

function Get-Python312Executable {
    # Prefer the `py` launcher with explicit -3.12
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $py) {
        if (Test-PythonVersion -File 'py' -Args @('-3.12')) {
            return @('py', @('-3.12'))
        }
    }

    # Try common command names
    foreach ($candidate in @('python3.12', 'python312', 'python')) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $cmd -and (Test-PythonVersion -File $candidate -Args @())) {
            return @($candidate, @())
        }
    }

    throw 'Python 3.12 not found. Install Python 3.12 (https://www.python.org/downloads/release/python-3120/) or ensure the `py` launcher can locate it via `py -3.12`, then re-run.'
}

function Ensure-AzLoggedIn {
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        throw 'Azure CLI (`az`) not found. Install Azure CLI and re-run.'
    }

    & az account show --only-show-errors | Out-Null
    if ($LASTEXITCODE -eq 0) {
        return
    }

    Write-Host 'Azure CLI not logged in. Running `az login`...' -ForegroundColor Yellow
    Invoke-Checked -File 'az' -Args @('login')
}

function Install-PublicBootstrapPackages {
    param(
        [Parameter(Mandatory = $true)][string]$PythonExe
    )

    Write-Host 'Installing keyring packages from public PyPI ...' -ForegroundColor Yellow
    Invoke-Checked -File $PythonExe -Args @(
        '-m', 'pip', 'install',
        '--index-url', 'https://pypi.org/simple',
        'keyring',
        'artifacts-keyring'
    )
}

$scriptDir = $PSScriptRoot
$zeroToilRoot = Resolve-Path (Join-Path $scriptDir '..')
$feedUrl = 'https://msazure.pkgs.visualstudio.com/One/_packaging/Storage-XI-feed/pypi/simple/'

Push-Location $zeroToilRoot
try {
    Write-Host "Working directory: $zeroToilRoot" -ForegroundColor Cyan

    if (-not [string]::IsNullOrWhiteSpace($Version)) {
        Write-Host 'Version parameter is ignored. Use zero-toil/pyproject.toml for version pinning.' -ForegroundColor Yellow
    }

    # 1) Create venv under zero-toil/.venv
    $venvDir = Join-Path $zeroToilRoot '.venv'
    $venvPython = Join-Path $venvDir 'Scripts\python.exe'

    if (-not (Test-Path $venvPython)) {
        $pythonInfo = Get-Python312Executable
        $pythonExe = $pythonInfo[0]
        $pythonArgs = [string[]]$pythonInfo[1]

        Write-Host "Creating Python 3.12 venv at zero-toil/.venv (using $pythonExe $($pythonArgs -join ' ')) ..." -ForegroundColor Yellow
        Invoke-Checked -File $pythonExe -Args ($pythonArgs + @('-m', 'venv', $venvDir))
    } else {
        Write-Host 'Venv already exists. Skipping creation.' -ForegroundColor DarkGray
    }

    Write-Host 'Upgrading pip ...' -ForegroundColor Yellow
    Invoke-Checked -File $venvPython -Args @('-m', 'pip', 'install', '--upgrade', 'pip')

    # 2) Ensure local Azure CLI session is available for feed authentication
    Ensure-AzLoggedIn

    # 3) Install keyring dependencies from public PyPI for feed auth
    Install-PublicBootstrapPackages -PythonExe $venvPython

    # 4) Install zerotoil + test/dev dependencies from Storage-XI-feed (managed by pyproject.toml)
    Write-Host 'Installing zerotoil with test/dev dependencies from One/Storage-XI-feed ...' -ForegroundColor Yellow
    Invoke-Checked -File $venvPython -Args @(
        '-m', 'pip', 'install',
        '--index-url', $feedUrl,
        '-e', '.[test,dev]'
    )

    # 4b) Force-upgrade unpinned internal packages to latest from the feed.
    # pyproject.toml leaves these unpinned; without --upgrade pip keeps the cached
    # version forever, so re-running prepare_env never picks up new xportal/xds/xstore builds.
    Write-Host 'Upgrading internal packages (xportal, xds-client, xstore, xaiops, xrhc) to latest ...' -ForegroundColor Yellow
    Invoke-Checked -File $venvPython -Args @(
        '-m', 'pip', 'install',
        '--index-url', $feedUrl,
        '--upgrade',
        'xportal', 'xds-client', 'xstore', 'xaiops', 'xrhc'
    )

    # 5) Verify local Python environment and XPortal authentication/connectivity
    Write-Host 'Running ZeroToil XPortal smoke test ...' -ForegroundColor Yellow
    Invoke-Checked -File $venvPython -Args @((Join-Path $scriptDir 'post_usage_smoketest.py'))

    Write-Host 'Done.' -ForegroundColor Green
    Write-Host 'Activate the venv with:' -ForegroundColor Cyan
    Write-Host '  .\.venv\Scripts\Activate.ps1' -ForegroundColor Cyan
} finally {
    Pop-Location
}
