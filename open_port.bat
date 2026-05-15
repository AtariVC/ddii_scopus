New-NetFirewallRule `
  -DisplayName "ddii_tcp 5012 ZeroTier" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 5012 `
  -Profile Any