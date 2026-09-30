"""
Example usage of OKX Trading Bot
Demonstrates all core functions
"""

from okx_trading_bot import OKXTradingBot
import json

def main():
    # Initialize bot with your credentials
    bot = OKXTradingBot(
        api_key='YOUR_API_KEY',
        secret_key='YOUR_SECRET_KEY',
        passphrase='YOUR_PASSPHRASE',
        sandbox=True,  # Start with sandbox for testing
        region='global'
    )
    
    print('\n' + '='*70)
    print('OKX SPOT TRADING BOT - EXAMPLE USAGE')
    print('='*70)
    
    # Step 1: Check Account Balance
    print('\n[STEP 1] Checking account balance...')
    balance_response = bot.check_account_balance()
    if balance_response.get('code') != '0':
        print(f'[ERROR] Could not fetch balance: {balance_response}')
        return
    
    # Step 2: Verify Instrument Exists
    print('\n[STEP 2] Verifying BTC-USDT instrument...')
    instrument_response = bot.check_instrument('BTC-USDT')
    if instrument_response.get('code') != '0':
        print(f'[ERROR] Instrument check failed: {instrument_response}')
        return
    
    # Step 3: Place Market Buy Order
    print('\n[STEP 3] Placing market buy order...')
    market_order_response = bot.place_market_order(
        symbol='BTC-USDT',
        side='buy',
        size='0.001',
        run_pre_flight_checks=False  # Skip checks since we just ran them
    )
    
    if market_order_response.get('code') == '0':
        order_id = market_order_response['data'][0]['ordId']
        print(f'[SUCCESS] Market order placed with ID: {order_id}')
    else:
        print(f'[ERROR] Market order failed: {market_order_response}')
    
    # Step 4: Place Limit Buy Order
    print('\n[STEP 4] Placing limit buy order...')
    limit_order_response = bot.place_limit_order(
        symbol='ETH-USDT',
        side='buy',
        size='0.01',
        price='2500',
        run_pre_flight_checks=True  # Run checks for this order
    )
    
    if limit_order_response.get('code') == '0':
        order_id = limit_order_response['data'][0]['ordId']
        print(f'[SUCCESS] Limit order placed with ID: {order_id}')
    else:
        print(f'[ERROR] Limit order failed: {limit_order_response}')
    
    # Step 5: Example of catching error
    print('\n[STEP 5] Testing error handling (invalid instrument)...')
    invalid_response = bot.check_instrument('INVALID-USDT')
    print(f'Expected error: {invalid_response}')
    
    print('\n' + '='*70)
    print('EXAMPLE COMPLETE')
    print('='*70)

if __name__ == '__main__':
    main()
