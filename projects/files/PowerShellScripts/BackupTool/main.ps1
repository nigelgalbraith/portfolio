# CLOUD STORAGE BACKUP TOOL #

# CONSTANTS
$CONFIG_PATH = "$PSScriptRoot\config\mainConfig.json"

# ============ DEPENDENCIES ============
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.IO.Compression.FileSystem
# ======================================

# ============ MODULE IMPORTS ============
# Import Core Modules
Import-Module "$PSScriptRoot\modules\Core\BackupConfig.psm1" -Force -Verbose
Import-Module "$PSScriptRoot\modules\Core\BackupCore.psm1" -Force -Verbose

# Import GUI Modules
Import-Module "$PSScriptRoot\modules\GUI\BackupUI.psm1" -Force -Verbose
Import-Module "$PSScriptRoot\modules\GUI\FileSystemUI.psm1" -Force -Verbose

# ============ APPLICATION ENTRY POINT ============

# Entry point for the Cloud Backup Tool GUI; initializes components, loads settings, and handles events.
function Main {
    <#
    .SYNOPSIS
    Launches the Cloud Backup Tool GUI.

    .DESCRIPTION
    Entry point for initializing configuration, creating UI components, and wiring up backup logic.
    This function sets up the full form layout, loads provider definitions and user settings, 
    and attaches actions for Backup, Cancel, and Shutdown operations.
    #>
    try {
        # ------------------------------
        # LOAD CONFIGURATION AND RESOURCES
        # ------------------------------

        $config = Convert-ToHashtable (Import-JsonFile -JsonPath $CONFIG_PATH)

        # Load cloud providers and current saved settings
        $cloud_providers = Convert-ToHashtable (Import-JsonFile -jsonPath $config.Locations.ProviderPath)
        $settings = Initialize-BackupSettings -settingsPath $config.Locations.SettingsPath -providers $cloud_providers

        # ------------------------------
        # EXTRACT UI LAYOUT DEFINITIONS
        # ------------------------------
        $form_layout = @{
            formWidth     = $config.Form.Width
            formHeight    = $config.Form.Height
            startPosition = $config.Form.StartPosition
            defaultFont   = $config.Fonts.Default
        }

        $tab_layout = @{
            tabWidth  = $config.Layout.TabControl.Width
            tabHeight = $config.Layout.TabControl.Height
            tabX      = $config.Layout.TabControl.X
            tabY      = $config.Layout.TabControl.Y
        }

        $provider_layout = @{
            XLeftMargin           = $config.Margins.Left
            XLabelOffset          = $config.Offset.LabelX
            YLineSpacing          = $config.Spacing.YLine
            YSmallSpacing         = $config.Spacing.YSmall
            LabelWidth            = $config.Layout.Labels.Width
            TextBoxWidth          = $config.Layout.TextBoxes.Width
            BrowseButtonHeight    = $config.Layout.BrowseButtons.Height
            BrowseButtonWidth     = $config.Layout.BrowseButtons.Width
            TextBoxHeightSrc      = $config.Layout.TextBoxes.HeightSrc
            TextBoxHeightDest     = $config.Layout.TextBoxes.HeightDest
            GroupBoxWidth         = $config.Layout.GroupBoxes.Width
            GroupBoxHeight        = $config.Layout.GroupBoxes.Height
            HeaderWidth           = $config.Layout.Headers.Width
            HeaderHeight          = $config.Layout.Headers.Height
            ExplainLabelWidth     = $config.Layout.ExplainLabels.Width
            ExplainLabelHeight    = $config.Layout.ExplainLabels.Height
            ComboBoxWidth         = $config.Layout.ComboBoxes.Width
            NumericWidth          = $config.Layout.NumericInputs.Width
            ModeExplainTextColor  = $config.Colors.ModeExplainText
            ExplainTextColor      = $config.Colors.ExplainText
            DefaultFrequencies    = $config.Defaults.Frequencies
            DefaultKeepCount      = $config.Defaults.KeepCount
            HeaderFont            = $config.Fonts.Header
            InnerRadioY           = $config.Offsets.InnerRadioY
            LabelX                = $config.Layout.Labels.X
            TextBoxX              = $config.Layout.TextBoxes.X
            BrowseButtonX         = $config.Layout.BrowseButtons.X
            TreeFormWidth         = $config.Tree.Form.Width
            TreeFormHeight        = $config.Tree.Form.Height
            TreeX                 = $config.Tree.TreeView.X
            TreeY                 = $config.Tree.TreeView.Y
            TreeWidth             = $config.Tree.TreeView.Width
            TreeHeight            = $config.Tree.TreeView.Height
            TreeOKX               = $config.Tree.Buttons.OK.X
            TreeOKY               = $config.Tree.Buttons.OK.Y
            TreeCancelX           = $config.Tree.Buttons.Cancel.X
            TreeCancelY           = $config.Tree.Buttons.Cancel.Y
            TreeButtonWidth       = $config.Tree.Buttons.Width
            TreeButtonHeight      = $config.Tree.Buttons.Height
        }

        $progress_layout = @{
            X      = $config.Layout.TabControl.X
            Y      = $config.Layout.ProgressBar.Y
            Width  = $config.Layout.TabControl.Width - 20
            Height = $config.Layout.ProgressBar.Height
        }

        $logbox_layout = @{
            X         = $config.Layout.TabControl.X
            Y         = $config.Layout.LogBox.Y
            Width     = $config.Layout.TabControl.Width - 10
            Height    = $config.Layout.LogBox.Height
            BackColor = $config.Colors.LogBoxBack
            ForeColor = $config.Colors.LogBoxFore
            Font      = $config.Fonts.Log
        }

        $button_layout = @{
            formWidth     = $config.Form.Width
            buttonHeight  = $config.Layout.Buttons.Height
            startY        = $config.Layout.Buttons.Y
            cancelWidth   = $config.Layout.Buttons.Cancel.Width
            backupWidth   = $config.Layout.Buttons.Backup.Width
            shutdownWidth = $config.Layout.Buttons.Shutdown.Width
            spacing       = $config.Spacing.Btn
        }

        $robocopy_settings = @{
            Retries           = $config.Robocopy.Retries
            Wait              = $config.Robocopy.Wait
            Threads           = $config.Robocopy.Threads
            PostBackupDelay   = $config.Robocopy.PostBackupDelay
            SyncCheckInterval = $config.Robocopy.SyncCheckInterval
        }
        
        # ------------------------------
        # CREATE UI COMPONENTS
        # ------------------------------

        $form       = New-MainForm @form_layout
        $controlMap = @{}

        $tabControl = New-ProviderTabs `
            -providers $cloud_providers `
            -settings $settings `
            -controlMap ([ref]$controlMap) `
            @tab_layout `
            -providerLayout $provider_layout

        $progressBar = New-ProgressBar @progress_layout
        $logBox      = New-LogBox @logbox_layout
        $buttons     = New-Buttons @button_layout

        # Add components to the form
        $form.Controls.AddRange(@(
            $tabControl, $progressBar, $logBox,
            $buttons.Cancel, $buttons.Backup, $buttons.Shutdown
        ))

        # ------------------------------
        # CREATE GUI CONTEXT OBJECT
        # ------------------------------

        $gui = [PSCustomObject]@{
            Form        = $form
            LogBox      = $logBox
            ProgressBar = $progressBar
            BtnCancel   = $buttons.Cancel
            BtnBackup   = $buttons.Backup
            BtnShutdown = $buttons.Shutdown
        }

        # Add all control references (e.g., TxtGDriveSource) to GUI
        foreach ($key in $controlMap.Keys) {
            $gui | Add-Member -MemberType NoteProperty -Name $key -Value $controlMap[$key]
        }

        # ------------------------------
        # WIRE UP BUTTON EVENTS
        # ------------------------------

        # Cancel button: closes the form
        $gui.BtnCancel.Add_Click({ $gui.Form.Close() })

        # Backup button
        $gui.BtnBackup.Add_Click({
            Save-CurrentSettings -gui $gui -providers $cloud_providers -settingsPath $config.Locations.SettingsPath
            $jobs    = New-BackupJobs -gui $gui -cloud_providers $cloud_providers
            $result  = Get-ValidBackupJobs -jobs $jobs -cloud_providers $cloud_providers -logBox $gui.LogBox
            $valid   = $result.ValidJobs
            $errors  = $result.Errors

            if ($errors.Count -gt 0) {
                foreach ($err in $errors) { Write-Log -logBox $gui.LogBox -message $err -Error }
                Write-Log -logBox $gui.LogBox -message "One or more jobs are invalid. Backup cancelled." -Error
                return
            }

            Start-BackupProcess -jobs $valid -gui $gui -copySettings $robocopy_settings
            $gui.Form.Close()
        })

        # Backup + Shutdown button
        $gui.BtnShutdown.Add_Click({
            Save-CurrentSettings -gui $gui -providers $cloud_providers -settingsPath $config.Locations.SettingsPath
            $jobs    = New-BackupJobs -gui $gui -cloud_providers $cloud_providers
            $result  = Get-ValidBackupJobs -jobs $jobs -cloud_providers $cloud_providers -logBox $gui.LogBox
            $valid   = $result.ValidJobs
            $errors  = $result.Errors

            if ($errors.Count -gt 0) {
                foreach ($err in $errors) { Write-Log -logBox $gui.LogBox -message $err -Error }
                Write-Log -logBox $gui.LogBox -message "One or more jobs are invalid. Backup cancelled." -Error
                return
            }

            Start-BackupProcess -jobs $valid -gui $gui -copySettings $robocopy_settings
            Write-Log -logBox $gui.LogBox -message "Initiating system shutdown..."
            Stop-Computer -Force
        })

        # ------------------------------
        # DISPLAY THE FORM
        # ------------------------------
        [void]$form.ShowDialog()
    }
    catch {
        [System.Windows.Forms.MessageBox]::Show("Fatal error: $($_.Exception.Message)", "Error", 'OK', 'Error')
    }
}


# Start the application
Main