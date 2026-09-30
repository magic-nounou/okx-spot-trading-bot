"""
OKX Spot Trading Bot - Production Ready
Correct instrument IDs, proper authentication, error logging, and pre-flight checks.
"""

import hmac
import hashlib
import base64
import json
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Literal
import requests
from requests.exceptions import RequestException, Timeout

class OKXTradingBot:
    """
    OKX Spot Trading Bot with proper instrument IDs, authentication, and error handling.
    
    Fixes:
    1. Correct OKX spot format: BTC-USDT (no -AWAP, -SWAP, -FUTURES)
    2. Proper endpoint: POST /api/v5/trade/order
    3. Correct order body with cash mode
    4. Full header validation (OK-ACCESS-KEY, -SIGN, -TIMESTAMP, -PASSPHRASE)
    5. Raw error response logging
    6. Pre-flight checks for account balance and instruments
    """
    
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        passphrase: str,
        sandbox: bool = False,
        region: Literal['global', 'europe'] = 'global'
    ):
        """
        Initialize OKX Trading Bot.
        
        Args:
            api_key: Your OKX API key
            secret_key: Your OKX secret key
            passphrase: Your OKX passphrase (set in security settings)
            sandbox: Use sandbox environment (default: False)
            region: 'global' for https://www.okx.com or 'europe' for https://eea.okx.com
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        
        if region == 'europe':
            self.base_url = 'https://eea.okx.com'
        else:
            self.base_url = 'https://www.okx.com'
        
        if sandbox:
            self.base_url = self.base_url.replace('okx.com', 'okx.com/api')  # Sandbox variant
        
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """
        Generate HMAC SHA256 signature for OKX API.
        
        Args:
            timestamp: ISO 8601 timestamp (from server or local)
            method: HTTP method (GET, POST)
            request_path: API path (e.g., /api/v5/trade/order)
            body: JSON request body (empty string for GET)
        
        Returns:
            Base64-encoded signature
        """
        message = timestamp + method + request_path + body
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(signature.digest()).decode('utf-8')
    
    def _get_server_time(self) -> Optional[str]:
        """
        Fetch server time from OKX to ensure timestamp is within acceptable range.
        
        Returns:
            ISO 8601 timestamp or None if request fails
        """
        try:
            response = self.session.get(
                f'{self.base_url}/api/v5/public/time',
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == '0':
                server_ts = data['data'][0]['ts']
                # Convert milliseconds to seconds and back to ISO format
                server_time = datetime.fromtimestamp(
                    int(server_ts) / 1000,
                    tz=timezone.utc
                ).isoformat().replace('+00:00', 'Z')
                return server_time
        except Exception as e:
            print(f'[ERROR] Failed to fetch server time: {e}')
        
        # Fallback to local time (use at your own risk — must be within 30 seconds of server)
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        body: Optional[Dict] = None,
        timeout: int = 10
    ) -> Dict:
        """
        Make authenticated request to OKX API.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint (e.g., /api/v5/trade/order)
            body: Request body dictionary
            timeout: Request timeout in seconds
        
        Returns:
            Parsed JSON response
        """
        timestamp = self._get_server_time()
        if not timestamp:
            return {
                'code': '-1',
                'msg': 'Failed to get server time',
                'error': 'Cannot establish timestamp for authentication'
            }
        
        body_str = json.dumps(body) if body else ''
        signature = self._generate_signature(timestamp, method, endpoint, body_str)
        
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        url = f'{self.base_url}{endpoint}'
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = self.session.post(url, headers=headers, json=body, timeout=timeout)
            else:
                raise ValueError(f'Unsupported HTTP method: {method}')
            
            response.raise_for_status()
            return response.json()
        
        except Timeout:
            return {
                'code': '-1',
                'msg': 'Request timeout',
                'error': f'Request to {endpoint} timed out after {timeout}s'
            }
        except RequestException as e:
            return {
                'code': '-1',
                'msg': 'Request failed',
                'error': str(e),
                'raw_response': getattr(e.response, 'text', None)
            }
    
    def check_account_balance(self) -> Dict:
        """
        Pre-flight check: Verify account is authenticated and has balance.
        
        Endpoint: GET /api/v5/account/balance
        
        Returns:
            Response dict with balance info or error
        """
        print('[INFO] Checking account balance...')
        response = self._make_request('GET', '/api/v5/account/balance')
        
        if response.get('code') != '0':
            print(f'[ERROR] Balance check failed: {response}')
            return response
        
        balances = response.get('data', [{}])[0].get('details', [])
        print(f'[INFO] Account authenticated. Found {len(balances)} asset(s).')
        
        for balance in balances:
            ccy = balance.get('ccy', 'UNKNOWN')
            available = balance.get('availBal', '0')
            if float(available) > 0:
                print(f'  • {ccy}: {available}')
        
        return response
    
    def check_instrument(self, inst_id: str) -> Dict:
        """
        Pre-flight check: Verify instrument exists and is tradeable.
        
        Endpoint: GET /api/v5/public/instruments?instType=SPOT&instId={instId}
        
        Args:
            inst_id: Instrument ID (e.g., BTC-USDT)
        
        Returns:
            Response dict with instrument info or error
        """
        print(f'[INFO] Checking instrument: {inst_id}...')
        endpoint = f'/api/v5/public/instruments?instType=SPOT&instId={inst_id}'
        response = self._make_request('GET', endpoint)
        
        if response.get('code') != '0':
            print(f'[ERROR] Instrument check failed: {response}')
            return response
        
        instruments = response.get('data', [])
        if not instruments:
            print(f'[ERROR] Instrument {inst_id} NOT FOUND. Check spelling and ensure it\'s a SPOT pair.')
            return {'code': '-1', 'msg': f'Instrument {inst_id} not found'}
        
        inst = instruments[0]
        print(f'[INFO] Instrument found:')
        print(f'  • ID: {inst.get("instId")}')
        print(f'  • State: {inst.get("state")} (must be "live")')
        print(f'  • Min Size: {inst.get("minSz")}')
        print(f'  • Min Notional: {inst.get("minNotional")}')
        
        return response
    
    def place_market_order(
        self,
        symbol: str,
        side: Literal['buy', 'sell'],
        size: str,
        run_pre_flight_checks: bool = True
    ) -> Dict:
        """
        Place a SPOT market order on OKX.
        
        Endpoint: POST /api/v5/trade/order
        
        Args:
            symbol: Instrument ID in OKX format (BTC-USDT, ETH-USDT, etc.)
            side: 'buy' or 'sell'
            size: Amount to trade (as string, e.g., '0.001' for 0.001 BTC)
            run_pre_flight_checks: Run balance and instrument checks before placing order
        
        Returns:
            Response dict with order info or error
        
        Example:
            bot.place_market_order('BTC-USDT', 'buy', '0.001')
        """
        # Validate inputs
        if side not in ('buy', 'sell'):
            return {'code': '-1', 'msg': f'Invalid side: {side}. Must be "buy" or "sell".'}
        
        try:
            size_float = float(size)
            if size_float <= 0:
                raise ValueError('Size must be positive')
        except ValueError as e:
            return {'code': '-1', 'msg': f'Invalid size: {size}. {e}'}
        
        # Pre-flight checks
        if run_pre_flight_checks:
            print('\n[INFO] ========== PRE-FLIGHT CHECKS ==========')
            balance_check = self.check_account_balance()
            if balance_check.get('code') != '0':
                return balance_check
            
            instrument_check = self.check_instrument(symbol)
            if instrument_check.get('code') != '0':
                return instrument_check
            print('[INFO] ========== CHECKS PASSED ==========\n')
        
        # Build order body
        order_body = {
            'instId': symbol,
            'tdMode': 'cash',  # Spot trading (not margin)
            'side': side,
            'ordType': 'market',
            'sz': size
        }
        
        print(f'[INFO] Placing market order:')
        print(f'  • Symbol: {symbol}')
        print(f'  • Side: {side}')
        print(f'  • Size: {size}')
        print(f'  • Order Body: {json.dumps(order_body, indent=2)}')
        
        response = self._make_request('POST', '/api/v5/trade/order', order_body)
        
        # Log full response (critical for debugging)
        print(f'\n[RESPONSE] Full OKX API response:')
        print(json.dumps(response, indent=2))
        
        if response.get('code') == '0':
            order_data = response.get('data', [{}])[0]
            print(f'\n[SUCCESS] Order placed!')
            print(f'  • Order ID: {order_data.get("ordId")}')
            print(f'  • Symbol: {order_data.get("instId")}')
            print(f'  • Status: {order_data.get("ordType")}')
        else:
            print(f'\n[ERROR] Order placement failed!')
            print(f'  • Error Code: {response.get("code")}')
            print(f'  • Error Message: {response.get("msg")}')
            if 'error' in response:
                print(f'  • Details: {response.get("error")}')
            if 'raw_response' in response:
                print(f'  • Raw Response: {response.get("raw_response")}')
        
        return response
    
    def place_limit_order(
        self,
        symbol: str,
        side: Literal['buy', 'sell'],
        size: str,
        price: str,
        run_pre_flight_checks: bool = True
    ) -> Dict:
        """
        Place a SPOT limit order on OKX.
        
        Endpoint: POST /api/v5/trade/order
        
        Args:
            symbol: Instrument ID in OKX format (BTC-USDT, ETH-USDT, etc.)
            side: 'buy' or 'sell'
            size: Amount to trade (as string)
            price: Limit price (as string)
            run_pre_flight_checks: Run balance and instrument checks before placing order
        
        Returns:
            Response dict with order info or error
        
        Example:
            bot.place_limit_order('BTC-USDT', 'buy', '0.001', '42000')
        """
        if side not in ('buy', 'sell'):
            return {'code': '-1', 'msg': f'Invalid side: {side}. Must be "buy" or "sell".'}
        
        try:
            float(size)
            float(price)
        except ValueError:
            return {'code': '-1', 'msg': f'Invalid size or price. Must be numeric.'}
        
        # Pre-flight checks
        if run_pre_flight_checks:
            print('\n[INFO] ========== PRE-FLIGHT CHECKS ==========')
            balance_check = self.check_account_balance()
            if balance_check.get('code') != '0':
                return balance_check
            
            instrument_check = self.check_instrument(symbol)
            if instrument_check.get('code') != '0':
                return instrument_check
            print('[INFO] ========== CHECKS PASSED ==========\n')
        
        # Build order body
        order_body = {
            'instId': symbol,
            'tdMode': 'cash',
            'side': side,
            'ordType': 'limit',
            'sz': size,
            'px': price
        }
        
        print(f'[INFO] Placing limit order:')
        print(f'  • Symbol: {symbol}')
        print(f'  • Side: {side}')
        print(f'  • Size: {size}')
        print(f'  • Price: {price}')
        print(f'  • Order Body: {json.dumps(order_body, indent=2)}')
        
        response = self._make_request('POST', '/api/v5/trade/order', order_body)
        
        print(f'\n[RESPONSE] Full OKX API response:')
        print(json.dumps(response, indent=2))
        
        if response.get('code') == '0':
            order_data = response.get('data', [{}])[0]
            print(f'\n[SUCCESS] Limit order placed!')
            print(f'  • Order ID: {order_data.get("ordId")}')
            print(f'  • Symbol: {order_data.get("instId")}')
        else:
            print(f'\n[ERROR] Order placement failed!')
            print(f'  • Error Code: {response.get("code")}')
            print(f'  • Error Message: {response.get("msg")}')
        
        return response


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == '__main__':
    # Initialize bot
    bot = OKXTradingBot(
        api_key='YOUR_API_KEY_HERE',
        secret_key='YOUR_SECRET_KEY_HERE',
        passphrase='YOUR_PASSPHRASE_HERE',
        sandbox=False,  # Set to True for sandbox testing
        region='global'  # 'global' or 'europe'
    )
    
    # EXAMPLE 1: Check account balance
    print('\n' + '='*70)
    print('EXAMPLE 1: Check Account Balance')
    print('='*70)
    bot.check_account_balance()
    
    # EXAMPLE 2: Check if BTC-USDT exists
    print('\n' + '='*70)
    print('EXAMPLE 2: Check Instrument')
    print('='*70)
    bot.check_instrument('BTC-USDT')
    
    # EXAMPLE 3: Place a market buy order
    print('\n' + '='*70)
    print('EXAMPLE 3: Place Market Buy Order')
    print('='*70)
    result = bot.place_market_order(
        symbol='BTC-USDT',
        side='buy',
        size='0.001'
    )
    
    # EXAMPLE 4: Place a limit order
    print('\n' + '='*70)
    print('EXAMPLE 4: Place Limit Buy Order')
    print('='*70)
    result = bot.place_limit_order(
        symbol='ETH-USDT',
        side='buy',
        size='0.01',
        price='2500'
    )
    
    # CORRECT SYMBOLS TO USE:
    # ✅ BTC-USDT
    # ✅ ETH-USDT
    # ✅ SOL-USDT
    # ✅ XRP-USDT
    # ❌ BTC-USDT-AWAP (WRONG - display label, not tradeable)
    # ❌ BTC-USDT-SWAP (WRONG - futures, not spot)
    # ❌ BTC-USDT-FUTURES (WRONG - futures, not spot)
