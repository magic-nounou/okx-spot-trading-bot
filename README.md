# OKX Spot Trading Bot

Production-ready Python trading bot for OKX Spot market with proper authentication, error handling, and pre-flight checks.

## Features

✅ **Correct Instrument IDs** - Uses proper OKX spot format (BTC-USDT, not BTC-USDT-AWAP)
✅ **Proper Authentication** - Full HMAC SHA256 signature implementation
✅ **Error Logging** - Prints full raw responses for debugging
✅ **Pre-Flight Checks** - Validates account balance and instrument before placing orders
✅ **Market & Limit Orders** - Support for both order types
✅ **Multi-Region** - Works with global (www.okx.com) or Europe (eea.okx.com) endpoints
✅ **Sandbox Testing** - Optional sandbox mode for safe testing

## Installation

```bash
pip install requests
```

## Setup

1. Get your OKX API credentials:
   - Log in to OKX
   - Go to Account → API Management
   - Create an API key and copy:
     - API Key
     - Secret Key
     - Passphrase

2. Initialize the bot:

```python
from okx_trading_bot import OKXTradingBot

bot = OKXTradingBot(
    api_key='your_api_key',
    secret_key='your_secret_key',
    passphrase='your_passphrase',
    sandbox=False,  # Set True for testing
    region='global'  # or 'europe'
)
```

## Usage

### Check Account Balance

```python
bot.check_account_balance()
```

Output:
```
[INFO] Checking account balance...
[INFO] Account authenticated. Found 3 asset(s).
  • BTC: 0.001
  • USDT: 1000.50
  • ETH: 0.1
```

### Check Instrument Exists

```python
bot.check_instrument('BTC-USDT')
```

Output:
```
[INFO] Checking instrument: BTC-USDT...
[INFO] Instrument found:
  • ID: BTC-USDT
  • State: live (must be "live")
  • Min Size: 0.00001
  • Min Notional: 10
```

### Place Market Order

```python
# Buy 0.001 BTC at market price
result = bot.place_market_order(
    symbol='BTC-USDT',
    side='buy',
    size='0.001'
)
```

### Place Limit Order

```python
# Buy 0.01 ETH at $2500 limit price
result = bot.place_limit_order(
    symbol='ETH-USDT',
    side='buy',
    size='0.01',
    price='2500'
)
```

## Correct Instrument IDs

### ✅ CORRECT (Spot Trading)
- `BTC-USDT`
- `ETH-USDT`
- `SOL-USDT`
- `XRP-USDT`
- `ADA-USDT`

### ❌ WRONG (Futures/Invalid)
- `BTC-USDT-AWAP` → Display label, NOT tradeable
- `BTC-USDT-SWAP` → Perpetual futures, not spot
- `BTC-USDT-FUTURES` → Expiring futures, not spot
- `BTC/USDT` → Wrong separator (use dash, not slash)

## Error Code 50030 Fix

Error 50030 typically means **invalid instrument ID**. This bot fixes it by:

1. Using correct format: `BTC-USDT` (not `BTC-USDT-AWAP`)
2. Validating instrument exists before placing order
3. Using proper endpoint: `POST /api/v5/trade/order`
4. Correct order body with `tdMode: "cash"` for spot trading

## Response Format

All methods return a dictionary with OKX API response:

```python
{
    'code': '0',  # '0' = success, other = error
    'msg': 'Order placed successfully',
    'data': [
        {
            'ordId': '123456789',
            'instId': 'BTC-USDT',
            'ordType': 'market',
            'clOrdId': ''
        }
    ]
}
```

## Troubleshooting

### Authentication Fails
- Verify API key, secret, and passphrase are correct
- Check that API key has trading permissions enabled
- Ensure timestamp is within 30 seconds of server time

### Instrument Not Found
- Use correct OKX format: `BTC-USDT` (not `BTC/USDT` or `BTCUSDT`)
- Verify it's a SPOT pair, not SWAP or FUTURES
- Check OKX website to confirm symbol exists

### Insufficient Balance
- Call `check_account_balance()` to verify funds
- Ensure size and price are within exchange limits

### Order Fails Silently
- Full response is printed to console
- Check error code and message in output
- Common codes: 51000 (param error), 50000 (order failed)

## Requirements

- Python 3.7+
- `requests` library

## License

MIT
