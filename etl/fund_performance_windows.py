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
            
    def calculate_role_period_rentability(self) -> None:
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
            idx_start = df.index[df['date'] == initial_date][0]
        except IndexError:
            raise ValueError(f"Subscription {initial_date.date()} of fund {fund_name} not found")
    
        df.at[idx_start, 'simulation_value'] = initial_value
    
        for i in range(idx_start + 1, len(df)):
            dia = df.at[i, 'date']
            anterior = df.at[i - 1, 'simulation_value']
    
            if pd.isnull(anterior):
                continue
    
            aporte = subscriptions.get(dia, 0)
            resgate = redemptions.get(dia, 0)
            base = anterior + aporte - resgate
            pct = df.at[i, 'quota_pct_change']
    
            df.at[i, 'simulation_value'] = base * (1 + pct) if pd.notnull(pct) else base
    
        return df
            
    def calculate_1m_3m_6m_12m_24m_rentability(self):
        self.rentability_per_period = {}
        
        for fund_name in self.quota_dfs:
            df = self.quota_dfs[fund_name].copy()
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
        
            ultima_data = df['date'].max()
            valor_final = df.loc[df['date'] == ultima_data, 'valor_simulado'].values[0]
        
            # Datas alvo
            periodos = {
                '1M': ultima_data - pd.DateOffset(months=1),
                '3M': ultima_data - pd.DateOffset(months=3),
                '6M': ultima_data - pd.DateOffset(months=6),
                '1A': ultima_data - pd.DateOffset(years=1),
                '2A': ultima_data - pd.DateOffset(years=2),
            }
            
            # YTD = desde o primeiro dia disponível no ano atual
            primeiro_util_do_ano = df[df['date'].dt.year == ultima_data.year]['date'].min()
            if pd.notnull(primeiro_util_do_ano):
                periodos['YTD'] = primeiro_util_do_ano
            
        
            resultados = []
            for label, data_inicio in periodos.items():
                # Pega o valor mais próximo em data anterior ou igual
                df_periodo = df[df['date'] <= data_inicio]
                if df_periodo.empty:
                    continue
                valor_inicio = df_periodo.iloc[-1]['valor_simulado']
                if valor_inicio == None:
                    print(f'{fund_name} com investimento feito em menos de {label}')
                    rendimento_bruto = 0
                    rendimento_pct = 0
                else:
                    rendimento_bruto = valor_final - valor_inicio
                    rendimento_pct = rendimento_bruto / valor_inicio
        
                resultados.append({
                    'período': label,
                    'rendimento_brl': rendimento_bruto,
                    'rendimento_pct': rendimento_pct
                })
        
            self.rentability_per_period[fund_name] = pd.DataFrame(resultados)
    
    def run(self):
        self.read_consolidated_files()
        self.read_movements_from_json()
        self.calculate_quota_variation()
        self.calculate_role_period_rentability()   
        # self.calculate_1m_3m_6m_12m_24m_rentability()
        #fazer os gráficos dos períodos

if __name__ == '__main__':
    temp = FundRentabilityCalculator('2025-06-30')
    temp.run()
