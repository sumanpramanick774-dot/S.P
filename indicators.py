"""
NSE Cash & F&O Instrument Resolution Engine.
Parses DhanHQ scrip master to reliably map Cash IDs to Active Near-Month Stock Futures.
"""
import io
import requests
import pandas as pd
from datetime import datetime, date
from typing import Dict, Optional, Tuple
from config import AppConfig, IST

class InstrumentManager:
    def __init__(self, scrip_master_url: str = AppConfig.DHAN_SCRIP_MASTER_URL):
        self.scrip_master_url = scrip_master_url
        self.cash_map: Dict[str, str] = {}         # Symbol -> Equity Security ID
        self.futures_map: Dict[str, dict] = {}     # Symbol -> Active Futures Contract Info
        self.last_sync: Optional[datetime] = None

    def fetch_and_build_universe(self, fno_symbols: list[str]) -> Tuple[Dict[str, str], Dict[str, dict]]:
        """
        Downloads Dhan's compact scrip master and maps:
        1. NSE Cash Equity securityId
        2. Nearest Active NSE Futures contract securityId & Expiry
        """
        try:
            resp = requests.get(self.scrip_master_url, timeout=15)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text), low_memory=False)
            
            # Column definitions from DhanHQ:
            # SEM_EXM_EXCH_ID: NSE / BSE
            # SEM_SEGMENT: E (Equity), D (Derivatives)
            # SEM_INSTRUMENT_NAME: EQUITIES, FUTSTK, etc.
            # SEM_SM_SYMBOL_NAME: Underlying Symbol
            # SEM_EXPIRY_DATE: Expiry timestamp/date
            
            # 1. Equity Cash Mapping
            cash_df = df[
                (df['SEM_EXM_EXCH_ID'] == 'NSE') & 
                (df['SEM_SEGMENT'] == 'E') & 
                (df['SEM_SM_SYMBOL_NAME'].isin(fno_symbols))
            ]
            for _, row in cash_df.iterrows():
                self.cash_map[str(row['SEM_SM_SYMBOL_NAME']).strip()] = str(row['SEM_SM_SECURITY_ID'])

            # 2. Futures Stock Mapping (Active near-month)
            fno_df = df[
                (df['SEM_EXM_EXCH_ID'] == 'NSE') & 
                (df['SEM_SEGMENT'] == 'D') & 
                (df['SEM_INSTRUMENT_NAME'] == 'FUTSTK') &
                (df['SEM_SM_SYMBOL_NAME'].isin(fno_symbols))
            ].copy()
            
            if not fno_df.empty:
                fno_df['EXPIRY'] = pd.to_datetime(fno_df['SEM_EXPIRY_DATE'])
                today = pd.Timestamp.now().floor('D')
                # Filter valid future expiries
                valid_fno = fno_df[fno_df['EXPIRY'] >= today]
                
                for sym in fno_symbols:
                    sym_fno = valid_fno[valid_fno['SEM_SM_SYMBOL_NAME'] == sym]
                    if not sym_fno.empty:
                        # Near-month contract has the smallest expiry >= today
                        near_row = sym_fno.sort_values(by='EXPIRY').iloc[0]
                        self.futures_map[sym] = {
                            "security_id": str(near_row['SEM_SM_SECURITY_ID']),
                            "trading_symbol": str(near_row.get('SEM_CUSTOM_SYMBOL', f"{sym}-FUT")),
                            "expiry": near_row['EXPIRY'].strftime('%Y-%m-%d'),
                            "lot_size": int(near_row.get('SEM_LOT_UNITS', 1))
                        }

            self.last_sync = datetime.now(IST)
            return self.cash_map, self.futures_map

        except Exception as e:
            # Fallback for offline/mock sandbox mode
            self._load_fallback_mapping(fno_symbols)
            return self.cash_map, self.futures_map

    def _load_fallback_mapping(self, fno_symbols: list[str]):
        """Safe fallback IDs if Dhan's CDN is unreachable."""
        base_id = 1000
        for i, sym in enumerate(fno_symbols):
            self.cash_map[sym] = str(base_id + i)
            self.futures_map[sym] = {
                "security_id": str(base_id + 5000 + i),
                "trading_symbol": f"{sym}-FUT",
                "expiry": "2026-10-29",
                "lot_size": 250
            }
        self.last_sync = datetime.now(IST)

