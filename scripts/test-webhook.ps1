# Prueba local del webhook sin WhatsApp real
$body = @{
    event = "message"
    device_id = "test@s.whatsapp.net"
    payload = @{
        id = "TEST001"
        from = "34600111222@s.whatsapp.net"
        body = "fiché entrada"
    }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://localhost:8000/webhook/whatsapp" -Method POST -Body $body -ContentType "application/json"
