function Set-Env {
<#
.SYNOPSIS
    A cross-platform utility to manage environment variables and the system PATH.
.DESCRIPTION
    This function sets or updates environment variables for the current session or persistently.
    It provides a dedicated mode for safely adding entries to the PATH variable, preventing duplicates.

    - Supports temporary (process/session) changes on all platforms.
    - Supports persistent changes for the current User or the entire System on Windows.
    - Automatically handles the correct PATH separator (';' on Windows, ':' on other platforms).
    - Prevents duplicate entries when adding to the PATH.
.PARAMETER Name
    The name of the environment variable to set. (Used in 'Variable' set).
.PARAMETER Value
    The value to assign to the variable, or the directory to add to the PATH.
.PARAMETER Path
    A switch to indicate that the 'Value' should be added to the PATH environment variable.
.PARAMETER Append
    If adding to the PATH, this switch appends the new value to the end. The default behavior is to prepend.
.PARAMETER Temporary
    Applies the change only to the current PowerShell session/process. This is the default scope.
.PARAMETER User
    Persists the change for the current user. (Windows-only).
.PARAMETER System
    Persists the change for the entire system (machine-wide). Requires administrator privileges. (Windows-only).
.EXAMPLE
    # Add a directory to the PATH for the current session only (cross-platform)
    Set-Env -Path -Value "/usr/local/bin"

.EXAMPLE
    # Persistently add a tool's directory to the user's PATH on Windows
    Set-Env -Path -Value "C:\tools\my-cli" -User

.EXAMPLE
    # Set a temporary API key for the current session
    Set-Env -Name "MY_API_KEY" -Value "abc12345" -Temporary

.EXAMPLE
    # Persistently set JAVA_HOME for the entire system on Windows (requires admin)
    Set-Env -Name "JAVA_HOME" -Value "C:\Program Files\Java\jdk-11" -System -Verbose

.EXAMPLE
    # See what would happen if you added a directory to the system PATH
    Set-Env -Path -Value "C:\ProgramData\chocolatey\bin" -System -WhatIf

.EXAMPLE
    # Add a directory to the end of the user PATH on Windows
    Set-Env -Path -Value "C:\Users\admin\scripts" -User -Append
#>
    [CmdletBinding(SupportsShouldProcess = $true, DefaultParameterSetName = 'Variable')]
    param (
        [Parameter(Mandatory = $true, ParameterSetName = 'Variable', Position = 0)]
        [string]$Name,

        [Parameter(Mandatory = $true, Position = 1)]
        [string]$Value,

        [Parameter(Mandatory = $true, ParameterSetName = 'Path')]
        [switch]$Path,

        [Parameter(ParameterSetName = 'Path')]
        [switch]$Append,

        [Parameter()]
        [switch]$Temporary,

        [Parameter()]
        [switch]$User,

        [Parameter()]
        [switch]$System
    )

    begin {
        # --- Parameter Validation and Setup ---
        $isWindows = $PSVersionTable.PSVersion.Major -ge 6 ? [System.Management.Automation.PowerShell.IsWindows] : $IsWindows

        # Ensure only one scope is selected
        $scopeSwitches = @($PSBoundParameters['Temporary'], $PSBoundParameters['User'], $PSBoundParameters['System']).Where({ $_ }).Count
        if ($scopeSwitches -gt 1) {
            throw "You can only specify one scope: -Temporary, -User, or -System."
        }

        # Determine the target scope
        $targetScope = 'Process' # Default to temporary/session
        if ($User) { $targetScope = 'User' }
        if ($System) { $targetScope = 'Machine' }

        # On non-Windows, persistent changes are not supported. Warn the user and force temporary scope.
        if (-not $isWindows -and ($targetScope -ne 'Process')) {
            Write-Warning "Persistent environment variables (-User, -System) are a Windows-only feature. Applying change to the current session only."
            $targetScope = 'Process'
        }

        # Determine the variable name and PATH separator
        $varName = if ($Path) { 'Path' } else { $Name }
        $pathSeparator = [System.IO.Path]::PathSeparator
    }

    process {
        $newValue = $Value
        $currentValue = ''
        $itemPath = "Env:$varName" # Path for provider cmdlets

        # --- Get Current Value ---
        if ($targetScope -eq 'Process') {
            # **FIXED HERE**: Using the robust Get-Item cmdlet to avoid parser errors.
            if (Test-Path $itemPath) {
                $currentValue = (Get-Item -Path $itemPath).Value
            }
        }
        else {
            # For User/Machine, we need the .NET method to get the non-expanded, raw value
            try {
                $currentValue = [System.Environment]::GetEnvironmentVariable($varName, $targetScope)
            }
            catch {
                throw "Failed to get environment variable '$varName' for scope '$targetScope'. If using -System, ensure you are running as an Administrator."
            }
        }

        # --- Construct New Value (special handling for PATH) ---
        if ($Path) {
            # Gracefully handle if the PATH variable doesn't exist yet
            $pathEntries = if ($currentValue) {
                $currentValue -split [regex]::Escape($pathSeparator) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
            } else {
                @()
            }
            
            # Use platform-specific comparison for path entries
            $comparison = if ($isWindows) { 'InvariantCultureIgnoreCase' } else { 'InvariantCulture' }
            if ($pathEntries.Contains($Value, [System.StringComparer]::$comparison)) {
                Write-Host "The path '$Value' already exists in the $targetScope PATH. No changes made."
                return # Exit gracefully
            }

            Write-Verbose "Adding '$Value' to the $targetScope PATH."
            if ($Append) {
                $newPathArray = $pathEntries + $Value
            }
            else {
                $newPathArray = @($Value) + $pathEntries
            }
            $newValue = $newPathArray -join $pathSeparator
        }

        # --- Perform the Action ---
        $action = "Set environment variable '$varName' for scope '$targetScope'"
        $target = "Name: $varName, Value: $($newValue.Substring(0, [System.Math]::Min($newValue.Length, 80)))..."

        if ($PSCmdlet.ShouldProcess($target, $action)) {
            try {
                if ($targetScope -eq 'Process') {
                    # **FIXED HERE**: Using the robust Set-Item cmdlet to avoid parser errors.
                    Set-Item -Path $itemPath -Value $newValue
                    Write-Host "Successfully set '$varName' for the current session."
                }
                else {
                    [System.Environment]::SetEnvironmentVariable($varName, $newValue, $targetScope)
                    Write-Host "Successfully set '$varName' for scope '$targetScope'. You may need to restart your shell or system for changes to take effect."
                }
            }
            catch {
                throw "Failed to set environment variable '$varName' for scope '$targetScope'. If using -System, ensure you are running as an Administrator."
            }
        }
    }
}
