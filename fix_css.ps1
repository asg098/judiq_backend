
$content = Get-Content 'styles.css' -Encoding UTF8 -Raw
# The corrupted part has null bytes which show up as spaces in some contexts
# Let's find the position of the first corrupted character
$corruptedStart = $content.IndexOf(". r e c e n t")
if ($corruptedStart -ge 0) {
    $cleanContent = $content.Substring(0, $corruptedStart)
    $cleanContent += ".recent-case-item {`n    cursor: pointer !important;`n}"
    Set-Content 'styles.css' -Value $cleanContent -Encoding UTF8
    Write-Host "Fixed styles.css"
} else {
    Write-Host "Could not find corrupted part"
}
