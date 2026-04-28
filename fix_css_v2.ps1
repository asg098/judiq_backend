
$lines = Get-Content 'styles.css'
$goodLines = @()
foreach ($line in $lines) {
    if ($line -like "*.*r*e*c*e*n*t*") { break }
    $goodLines += $line
}
$newContent = ($goodLines -join "`n") + "`n.recent-case-item {`n    cursor: pointer !important;`n}"
Set-Content 'styles.css' -Value $newContent -Encoding UTF8
Write-Host "Fixed styles.css via line iteration"
