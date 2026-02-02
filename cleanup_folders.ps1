# Folder Cleanup Script
# Consolidates all data to proper data/raw/ location

Write-Host "=" * 70
Write-Host "Cleaning up duplicate folders..."
Write-Host "=" * 70

$projectRoot = "d:\DATA SCIENCE\ncr_property_price_estimation"
$dataRaw = "$projectRoot\data\raw"

Write-Host "`nCurrent structure:"
Write-Host "  [CORRECT] data/raw/ - Main data location"
Write-Host "  [DELETE]  RealEstate_ML_Data/ - Duplicate at root"
Write-Host "  [DELETE]  ncr_property_price_estimation/data/RealEstate_ML_Data/ - Old location"

# 1. Delete root RealEstate_ML_Data (only has old logs)
Write-Host "`n1. Removing root RealEstate_ML_Data folder..."
$rootFolder = "$projectRoot\RealEstate_ML_Data"
if (Test-Path $rootFolder) {
    Remove-Item -Path $rootFolder -Recurse -Force
    Write-Host "   [OK] Deleted: $rootFolder"
} else {
    Write-Host "   [SKIP] Already deleted"
}

# 2. Delete old ncr_property_price_estimation/data/RealEstate_ML_Data
Write-Host "`n2. Removing old RealEstate_ML_Data from script directory..."
$oldFolder = "$projectRoot\ncr_property_price_estimation\data\RealEstate_ML_Data"
if (Test-Path $oldFolder) {
    # Check if it has any important data first
    $csvFile = "$oldFolder\99acres_NCR_ML_Final.csv"
    if (Test-Path $csvFile) {
        $oldSize = (Get-Item $csvFile).Length
        $newSize = (Get-Item "$dataRaw\99acres_NCR_ML_Final.csv").Length
        
        if ($newSize -ge $oldSize) {
            Write-Host "   [OK] New CSV is up-to-date (${newSize} bytes >= ${oldSize} bytes)"
            Remove-Item -Path $oldFolder -Recurse -Force
            Write-Host "   [OK] Deleted: $oldFolder"
        } else {
            Write-Host "   [WARNING] Old CSV is larger! Not deleting. Please check manually."
        }
    } else {
        Remove-Item -Path $oldFolder -Recurse -Force
        Write-Host "   [OK] Deleted: $oldFolder"
    }
} else {
    Write-Host "   [SKIP] Already deleted"
}

# 3. Verify data/raw/ has everything
Write-Host "`n3. Verifying data/raw/ contents..."
$csvPath = "$dataRaw\99acres_NCR_ML_Final.csv"
$checkpointPath = "$dataRaw\checkpoint.json"
$logsPath = "$dataRaw\logs"

if (Test-Path $csvPath) {
    $size = (Get-Item $csvPath).Length
    Write-Host "   [OK] CSV file: $size bytes"
} else {
    Write-Host "   [ERROR] CSV file missing!"
}

if (Test-Path $checkpointPath) {
    Write-Host "   [OK] Checkpoint file exists"
} else {
    Write-Host "   [WARNING] Checkpoint file missing (will be created on next run)"
}

if (Test-Path $logsPath) {
    $logCount = (Get-ChildItem -Path $logsPath -File).Count
    Write-Host "   [OK] Logs folder: $logCount files"
} else {
    Write-Host "   [WARNING] Logs folder missing (will be created on next run)"
}

Write-Host "`n" + "=" * 70
Write-Host "CLEANUP COMPLETE!"
Write-Host "=" * 70
Write-Host "`nFinal structure:"
Write-Host "  data/raw/"
Write-Host "    ├── 99acres_NCR_ML_Final.csv"
Write-Host "    ├── checkpoint.json"
Write-Host "    └── logs/"
Write-Host "        ├── scraper.log"
Write-Host "        └── scraper_errors.log"
Write-Host "`nAll data is now in the correct location!"
Write-Host "=" * 70
