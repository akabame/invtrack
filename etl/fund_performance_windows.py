import os
import pandas as pd
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_PATH = ROOT_DIR / "data" / "processed"
FUNDS_MOVEMENT_DATA_PATH = ROOT_DIR / "config" / "funds_movements.json"

class FundRentabilityCalculator():
    
    def __init__(self,date_report='2019-05-30'):
        self.date_report = date_report

    def read_consolidated_files(self) -> None:
        self.quota_dfs = {}
        
        # Loop through files in the directory
        for filename in os.listdir(PROCESSED_DATA_PATH):
            if filename.endswith('.xlsx'):
                filepath = os.path.join(PROCESSED_DATA_PATH, filename)
                df = pd.read_excel(filepath)
                key = os.path.splitext(filename)[0]  # filename without extension
                df = df[df['date']<=self.date_report]
                self.quota_dfs[key] = df
    
    def read_movements_from_json(self) -> None:
        with open(FUNDS_MOVEMENT_DATA_PATH, 'r', encoding='utf-8') as f:
            self.dfs_movement_history = json.load(f)
    
        for fund_data in self.dfs_movement_history.values():
            fund_data['initial_date'] = pd.to_datetime(fund_data['initial_date'])
            fund_data['subscriptions'] = {pd.to_datetime(k): v for k, v in fund_data['subscriptions'].items()}
            fund_data['redemptions'] = {pd.to_datetime(k): v for k, v in fund_data['redemptions'].items()}
    
    def calculate_quota_variation(self) -> None:
        for fund_name in self.quota_dfs:
            self.quota_dfs[fund_name]['quota_pct_change'] = self.quota_dfs[fund_name]['quota'].pct_change()
            self.quota_dfs[fund_name] = self.quota_dfs[fund_name][['date','quota','quota_pct_change']]
            
    def simulate_investment_evolution(self) -> None:
        for fund_name, movement in self.dfs_movement_history.items():
            if fund_name not in self.quota_dfs:
                print(f"[!] Fund {fund_name} not found in loaded quota data. Skipping.")
                continue
    
            df = self._prepare_fund_dataframe(fund_name)
            df = self._simulate_investment_evolution(df, movement, fund_name)
            self.quota_dfs[fund_name] = df
    
    def _prepare_fund_dataframe(self, fund_name:str) -> pd.DataFrame:
        df = self.quota_dfs[fund_name].copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
    
        if 'quota_pct_change' not in df.columns:
            df['quota_pct_change'] = df['quota'].pct_change()
    
        return df
    
    def _simulate_investment_evolution(self, df:pd.DataFrame, movement:dict, fund_name: str) -> pd.DataFrame:
        initial_date = movement['initial_date']
        initial_value = movement['initial_value']
        subscriptions = dict(movement.get('subscriptions', [])) 
        redemptions = dict(movement.get('redemptions', []))
    
        df['simulation_value'] = pd.NA
    
        try:
            idx_investment_start = df.index[df['date'] == initial_date][0]
        except IndexError:
            raise ValueError(f"Subscription {initial_date.date()} of fund {fund_name} not found")
    
        df.at[idx_investment_start, 'simulation_value'] = initial_value
    
        for idx_day in range(idx_investment_start + 1, len(df)):
            dia = df.at[idx_day, 'date']
            anterior = df.at[idx_day - 1, 'simulation_value']
    
            if pd.isnull(anterior):
                continue
    
            aporte = subscriptions.get(dia, 0)
            resgate = redemptions.get(dia, 0)
            base = anterior + aporte - resgate
            pct = df.at[idx_day, 'quota_pct_change']
    
            df.at[idx_day, 'simulation_value'] = base * (1 + pct) if pd.notnull(pct) else base
    
        return df
    
    def calculate_periodic_returns(self) -> None:
        self.rentability_per_period = {}
    
        for fund_name in self.quota_dfs:
            df = self._prepare_rentability_dataframe(fund_name)
            ultima_data = df['date'].max()
            valor_final = df.loc[df['date'] == ultima_data, 'simulation_value'].values[0]
            periodos = self._define_rentability_periods(df, ultima_data)
    
            resultados = [
                self._calculate_rentability_for_period(df, label, data_inicio, valor_final, fund_name)
                for label, data_inicio in periodos.items()
            ]
    
            self.rentability_per_period[fund_name] = pd.DataFrame(resultados)
    
    def _prepare_rentability_dataframe(self, fund_name: str) -> pd.DataFrame:
        df = self.quota_dfs[fund_name].copy()
        df['date'] = pd.to_datetime(df['date'])
        return df.sort_values('date').reset_index(drop=True)
            
    def _define_rentability_periods(self, df: pd.DataFrame, end_date: pd.Timestamp) -> dict:
        periodos = {
            '1M': end_date - pd.DateOffset(months=1),
            '3M': end_date - pd.DateOffset(months=3),
            '6M': end_date - pd.DateOffset(months=6),
            '1A': end_date - pd.DateOffset(years=1),
            '2A': end_date - pd.DateOffset(years=2),
        }
    
        primeiro_util = df[df['date'].dt.year == end_date.year]['date'].min()
        if pd.notnull(primeiro_util):
            periodos['YTD'] = primeiro_util
    
        return periodos
    
    def _calculate_rentability_for_period(self, df: pd.DataFrame, label: str, start_date: pd.Timestamp,
        final_value: float, fund_name: str) -> dict:
        
        df_periodo = df[df['date'] <= start_date]
        if df_periodo.empty:
            return {
                'período': label,
                'rendimento_brl': 0,
                'rendimento_pct': 0
            }
    
        valor_inicio = df_periodo.iloc[-1]['simulation_value']
        if valor_inicio is None or pd.isna(valor_inicio):
            print(f'{fund_name} com investimento feito em menos de {label}')
            return {
                'período': label,
                'rendimento_brl': 0,
                'rendimento_pct': 0
            }
    
        rendimento_brl = final_value - valor_inicio
        rendimento_pct = rendimento_brl / valor_inicio
    
        return {
            'período': label,
            'rendimento_brl': rendimento_brl,
            'rendimento_pct': rendimento_pct
        }
    
    def run(self):
        self.read_consolidated_files()
        self.read_movements_from_json()
        self.calculate_quota_variation()
        self.simulate_investment_evolution()   
        self.calculate_periodic_returns()
        #fazer os gráficos dos períodos

if __name__ == '__main__':
    temp = FundRentabilityCalculator('2025-06-30')
    temp.run()
