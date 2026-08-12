param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$MasterDir = Join-Path $ProjectRoot 'master'
$BackupDir = Join-Path $MasterDir 'backups'
$WorkoutFile = Join-Path $MasterDir 'workout_plan_master.xlsx'
$UserFile = Join-Path $MasterDir 'user_master.xlsx'
$ExerciseFile = Join-Path $MasterDir 'exercise_master.xlsx'

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
Copy-Item -LiteralPath $WorkoutFile -Destination (Join-Path $BackupDir "workout_plan_master_before_warning_fix_$stamp.xlsx")
Copy-Item -LiteralPath $UserFile -Destination (Join-Path $BackupDir "user_master_before_warning_fix_$stamp.xlsx")

function Normalize-Key($value) {
    return ([string]$value).Trim().ToLowerInvariant()
}

function To-JsonArray($values) {
    $unique = [System.Collections.Generic.List[string]]::new()
    $seen = @{}
    foreach ($value in $values) {
        $text = [string]$value
        if ([string]::IsNullOrWhiteSpace($text)) { continue }
        $key = Normalize-Key $text
        if (-not $seen.ContainsKey($key)) {
            $seen[$key] = $true
            $unique.Add($text.Trim())
        }
    }
    return '[' + (($unique | ForEach-Object { '"' + ($_.Replace('\', '\\').Replace('"', '\"')) + '"' }) -join ',') + ']'
}

function Parse-JsonArray($text) {
    if ([string]::IsNullOrWhiteSpace([string]$text)) { return @() }
    try {
        $parsed = ConvertFrom-Json -InputObject ([string]$text)
        if ($null -eq $parsed) { return @() }
        return @($parsed)
    } catch {
        return @()
    }
}

function Get-SharedStrings($zip) {
    $entry = $zip.GetEntry('xl/sharedStrings.xml')
    $items = [System.Collections.ArrayList]::new()
    if (-not $entry) { return $items }

    $reader = [System.IO.StreamReader]::new($entry.Open())
    [xml]$xml = $reader.ReadToEnd()
    $reader.Close()

    $ns = [System.Xml.XmlNamespaceManager]::new($xml.NameTable)
    $ns.AddNamespace('m', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')

    foreach ($si in $xml.SelectNodes('//m:si', $ns)) {
        $text = (($si.SelectNodes('.//m:t', $ns) | ForEach-Object { $_.InnerText }) -join '')
        [void]$items.Add($text)
    }

    return $items
}

function Get-CellText($cell, $sharedStrings) {
    if ($cell.t -eq 's') {
        return [string]$sharedStrings[[int]$cell.InnerText]
    }

    return [string]$cell.InnerText
}

function Get-ColumnName($cellRef) {
    return ([string]$cellRef) -replace '\d', ''
}

function Get-SheetEntryName($zip, $sheetName) {
    $reader = [System.IO.StreamReader]::new($zip.GetEntry('xl/workbook.xml').Open())
    [xml]$workbook = $reader.ReadToEnd()
    $reader.Close()

    $reader = [System.IO.StreamReader]::new($zip.GetEntry('xl/_rels/workbook.xml.rels').Open())
    [xml]$rels = $reader.ReadToEnd()
    $reader.Close()

    $ns = [System.Xml.XmlNamespaceManager]::new($workbook.NameTable)
    $ns.AddNamespace('m', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')
    $ns.AddNamespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')

    $sheet = $workbook.SelectNodes('//m:sheet', $ns) | Where-Object { $_.name -eq $sheetName } | Select-Object -First 1
    if (-not $sheet) { throw "Sheet not found: $sheetName" }

    $rid = $sheet.GetAttribute('id', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
    $target = ($rels.Relationships.Relationship | Where-Object { $_.Id -eq $rid }).Target
    $targetText = ([string]$target).TrimStart('/')
    if ($targetText.StartsWith('xl/')) {
        return $targetText
    }
    return ('xl/' + $targetText)
}

function Get-ColumnIndex($columnName) {
    $index = 0
    foreach ($char in ([string]$columnName).ToCharArray()) {
        $index = ($index * 26) + ([int][char]::ToUpperInvariant($char) - [int][char]'A' + 1)
    }
    return $index
}

function Get-OrCreateCell($xml, $ns, $cellRef) {
    $cell = $xml.SelectSingleNode("//m:c[@r='$cellRef']", $ns)
    if ($cell) { return $cell }

    $rowNumber = [int](([string]$cellRef) -replace '\D', '')
    $columnName = Get-ColumnName $cellRef
    $row = $xml.SelectSingleNode("//m:row[@r='$rowNumber']", $ns)
    if (-not $row) { throw "Row not found: $rowNumber" }

    $cell = $xml.CreateElement('c', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')
    $cell.SetAttribute('r', $cellRef)

    $inserted = $false
    $newIndex = Get-ColumnIndex $columnName
    foreach ($existing in $row.SelectNodes('m:c', $ns)) {
        if ((Get-ColumnIndex (Get-ColumnName $existing.r)) -gt $newIndex) {
            [void]$row.InsertBefore($cell, $existing)
            $inserted = $true
            break
        }
    }

    if (-not $inserted) {
        [void]$row.AppendChild($cell)
    }

    return $cell
}

function Read-XlsxSheet($path, $sheetName) {
    $rows = [System.Collections.ArrayList]::new()
    $fs = [System.IO.File]::Open((Resolve-Path $path), [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    $zip = [System.IO.Compression.ZipArchive]::new($fs, [System.IO.Compression.ZipArchiveMode]::Read)

    try {
        $sharedStrings = Get-SharedStrings $zip
        $entryName = Get-SheetEntryName $zip $sheetName
        $reader = [System.IO.StreamReader]::new($zip.GetEntry($entryName).Open())
        [xml]$xml = $reader.ReadToEnd()
        $reader.Close()

        $ns = [System.Xml.XmlNamespaceManager]::new($xml.NameTable)
        $ns.AddNamespace('m', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')

        $headers = @{}
        foreach ($row in $xml.SelectNodes('//m:sheetData/m:row', $ns)) {
            $rowNumber = [int]$row.r
            if ($rowNumber -eq 1) {
                foreach ($cell in $row.SelectNodes('m:c', $ns)) {
                    $headers[(Get-ColumnName $cell.r)] = Get-CellText $cell $sharedStrings
                }
                continue
            }

            $object = [ordered]@{ excel_row = $rowNumber }
            foreach ($cell in $row.SelectNodes('m:c', $ns)) {
                $name = $headers[(Get-ColumnName $cell.r)]
                if ($name) {
                    $object[$name] = Get-CellText $cell $sharedStrings
                }
            }
            [void]$rows.Add([pscustomobject]$object)
        }
    } finally {
        $zip.Dispose()
        $fs.Dispose()
    }

    return $rows
}

function Set-CellInlineText($xml, $ns, $cellRef, $text) {
    $cell = Get-OrCreateCell $xml $ns $cellRef

    while ($cell.HasChildNodes) {
        [void]$cell.RemoveChild($cell.FirstChild)
    }

    $cell.SetAttribute('t', 'inlineStr')
    $is = $xml.CreateElement('is', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')
    $t = $xml.CreateElement('t', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')
    $t.InnerText = [string]$text
    [void]$is.AppendChild($t)
    [void]$cell.AppendChild($is)
}

function Set-CellNumber($xml, $ns, $cellRef, $number) {
    $cell = Get-OrCreateCell $xml $ns $cellRef

    while ($cell.HasChildNodes) {
        [void]$cell.RemoveChild($cell.FirstChild)
    }

    if ($cell.HasAttribute('t')) {
        $cell.RemoveAttribute('t')
    }

    $v = $xml.CreateElement('v', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')
    $v.InnerText = [string]$number
    [void]$cell.AppendChild($v)
}

function Update-XlsxSheet($path, $sheetName, [scriptblock]$edit) {
    $fs = [System.IO.File]::Open((Resolve-Path $path), [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    $zip = [System.IO.Compression.ZipArchive]::new($fs, [System.IO.Compression.ZipArchiveMode]::Update)

    try {
        $sharedStrings = Get-SharedStrings $zip
        $entryName = Get-SheetEntryName $zip $sheetName
        $entry = $zip.GetEntry($entryName)
        $reader = [System.IO.StreamReader]::new($entry.Open())
        [xml]$xml = $reader.ReadToEnd()
        $reader.Close()

        $ns = [System.Xml.XmlNamespaceManager]::new($xml.NameTable)
        $ns.AddNamespace('m', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')

        $headersByName = @{}
        $headerRow = $xml.SelectSingleNode("//m:row[@r='1']", $ns)
        foreach ($cell in $headerRow.SelectNodes('m:c', $ns)) {
            $headersByName[(Get-CellText $cell $sharedStrings)] = Get-ColumnName $cell.r
        }

        & $edit $xml $ns $headersByName

        $entry.Delete()
        $newEntry = $zip.CreateEntry($entryName)
        $writer = [System.IO.StreamWriter]::new($newEntry.Open(), [System.Text.UTF8Encoding]::new($false))
        try {
            $xml.Save($writer)
        } finally {
            $writer.Dispose()
        }
    } finally {
        $zip.Dispose()
        $fs.Dispose()
    }
}

$exercises = @{}
foreach ($exercise in Read-XlsxSheet $ExerciseFile 'gym_exercise_dataset') {
    $exercises[$exercise.exercise_id] = $exercise
}

$plans = @{}
foreach ($plan in Read-XlsxSheet $WorkoutFile 'Workout_Plan') {
    $plans[$plan.plan_id] = $plan
}

$items = Read-XlsxSheet $WorkoutFile 'Workout_Plan_Items'
$users = @{}
foreach ($user in Read-XlsxSheet $UserFile 'User_Profile') {
    $users[$user.user_id] = $user
}

$goalsByUser = @{}
$coveredMusclesByUser = @{}
$weeklySetsByPlan = @{}
$itemsBySession = @{}

foreach ($item in $items) {
    $plan = $plans[$item.plan_id]
    if (-not $plan) { continue }

    $userId = $plan.user_id
    $exercise = $exercises[$item.exercise_id]
    if (-not $exercise) { continue }

    if (-not $goalsByUser.ContainsKey($userId)) { $goalsByUser[$userId] = [System.Collections.ArrayList]::new() }
    if (-not $coveredMusclesByUser.ContainsKey($userId)) { $coveredMusclesByUser[$userId] = @{} }

    foreach ($goal in Parse-JsonArray $exercise.recommended_goals) {
        [void]$goalsByUser[$userId].Add($goal)
    }

    if ([string]$item.week_number -eq '1' -and [string]$item.day_type -eq 'Training' -and [string]$item.set_type -ne 'Warm-up') {
        foreach ($muscle in Parse-JsonArray $exercise.primary_muscles) {
            $coveredMusclesByUser[$userId][(Normalize-Key $muscle)] = $muscle
        }

        if (-not $weeklySetsByPlan.ContainsKey($item.plan_id)) { $weeklySetsByPlan[$item.plan_id] = 0 }
        try {
            $weeklySetsByPlan[$item.plan_id] += [int]$item.sets
        } catch {
            $weeklySetsByPlan[$item.plan_id] += 0
        }
    }

    $sessionKey = "$($item.plan_id)|$($item.week_number)|$($item.day_number)"
    if (-not $itemsBySession.ContainsKey($sessionKey)) {
        $itemsBySession[$sessionKey] = [System.Collections.ArrayList]::new()
    }
    [void]$itemsBySession[$sessionKey].Add($item)
}

try {
    Update-XlsxSheet $UserFile 'User_Profile' {
        param($xml, $ns, $columns)

        foreach ($userId in $users.Keys) {
            $user = $users[$userId]
            $row = [int]$user.excel_row

            if ($goalsByUser.ContainsKey($userId)) {
                $goalValues = @()
                $goalValues += Parse-JsonArray $user.goal_filter_tags
                $goalValues += $goalsByUser[$userId]
                Set-CellInlineText $xml $ns "$($columns['goal_filter_tags'])$row" (To-JsonArray $goalValues)
            }

            $keptPriority = @()
            $covered = $coveredMusclesByUser[$userId]
            if ($covered) {
                foreach ($muscle in Parse-JsonArray $user.priority_muscles) {
                    if ($covered.ContainsKey((Normalize-Key $muscle))) {
                        $keptPriority += $muscle
                    }
                }
            }
            Set-CellInlineText $xml $ns "$($columns['priority_muscles'])$row" (To-JsonArray $keptPriority)
        }
    }
} catch {
    Write-Warning "Skipped User_Profile cleanup because user_master.xlsx is currently locked: $($_.Exception.Message)"
}

Update-XlsxSheet $WorkoutFile 'Workout_Plan' {
    param($xml, $ns, $columns)

    foreach ($planId in $plans.Keys) {
        $plan = $plans[$planId]
        $user = $users[$plan.user_id]
        if (-not $user) { continue }

        $row = [int]$plan.excel_row
        $preferredSplit = [string]$user.preferred_split
        if (-not [string]::IsNullOrWhiteSpace($preferredSplit) -and (Normalize-Key $preferredSplit) -ne 'auto') {
            Set-CellInlineText $xml $ns "$($columns['split_type'])$row" $preferredSplit
        }

        $currentSplit = if (-not [string]::IsNullOrWhiteSpace($preferredSplit) -and (Normalize-Key $preferredSplit) -ne 'auto') {
            $preferredSplit
        } else {
            [string]$plan.split_type
        }

        if ($currentSplit -eq 'Full Body') {
            $hasUpperBody = $false
            $hasLowerBody = $false

            foreach ($item in $items) {
                if ([string]$item.plan_id -ne [string]$planId) { continue }
                if ([string]$item.week_number -ne '1') { continue }
                if ([string]$item.day_type -ne 'Training') { continue }
                if ([string]$item.set_type -eq 'Warm-up') { continue }

                $exercise = $exercises[$item.exercise_id]
                if (-not $exercise) { continue }

                $bodyRegion = Normalize-Key $exercise.body_region
                if ($bodyRegion -eq 'upper body') { $hasUpperBody = $true }
                if ($bodyRegion -eq 'lower body') { $hasLowerBody = $true }
            }

            if (-not ($hasUpperBody -and $hasLowerBody)) {
                Set-CellInlineText $xml $ns "$($columns['split_type'])$row" 'Auto'
            }
        }

        $weekly = 0
        if ($weeklySetsByPlan.ContainsKey($planId)) {
            $weekly = $weeklySetsByPlan[$planId]
        }
        Set-CellNumber $xml $ns "$($columns['weekly_set_target'])$row" $weekly

        $days = 1
        try { $days = [int]$plan.days_per_week } catch { $days = 1 }
        if ($days -lt 1) { $days = 1 }
        $sessionVolume = [math]::Round($weekly / $days, 2)
        Set-CellNumber $xml $ns "$($columns['session_volume_target'])$row" $sessionVolume
    }
}

# Workout_Plan_Items structural cleanup is intentionally skipped in the fast pass.
Write-Output "Updated warning-prone fields."
Write-Output "Backups written to: $BackupDir"
