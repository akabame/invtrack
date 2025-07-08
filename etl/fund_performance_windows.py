import os
import pandas as pd
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_PATH = ROOT_DIR / "data" / "processed"

class FundRentabilityCalculator():
    
    def __init__(self,date_report='2025-05-30'):
        self.date_report = date_report

    def read_consolidated_files(self):
        self.quota_dfs = {}
        
        # Loop through files in the directory
        for filename in os.listdir(PROCESSED_DATA_PATH):
            if filename.endswith('.xlsx'):
                filepath = os.path.join(PROCESSED_DATA_PATH, filename)
                df = pd.read_excel(filepath)
                key = os.path.splitext(filename)[0]  # filename without extension
                df = df[df['date']<=self.date_report]
                self.quota_dfs[key] = df
    
    def calculate_quota_variation(self):
        for fund_name in self.quota_dfs:
            self.quota_dfs[fund_name]['quota_pct_change'] = self.quota_dfs[fund_name]['quota'].pct_change()
            self.quota_dfs[fund_name] = self.quota_dfs[fund_name][['date','quota','quota_pct_change']]
    
    def calculate_role_period_rentability(self):
        
        self.dfs_movement_history = {}
        
        #example
        self.dfs_movement_history['ALPINE FIM_consolidated_quota'] = {'data_aporte':'2025-01-02','valor_inicial':100000,'aportes':[],'resgates':[]}
        
        for fund_name in self.dfs_movement_history:
            df = self.quota_dfs[fund_name]
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
        
            if 'quota_pct_change' not in df.columns:
                df['quota_pct_change'] = df['quota'].pct_change()
        
            # Transforma aportes e resgates em dicionários para acesso rápido
            aportes_dict = {pd.to_datetime(d): v for d, v in self.dfs_movement_history[fund_name]['aportes']}
            resgates_dict = {pd.to_datetime(d): v for d, v in self.dfs_movement_history[fund_name]['resgates']}
        
            df['valor_simulado'] = None
        
            idx_inicial = df.index[df['date'] == pd.to_datetime(self.dfs_movement_history[fund_name]['data_aporte'])]
            if len(idx_inicial) == 0:
                raise ValueError(f"Data de aporte {self.dfs_movement_history[fund_name]['data_aporte']} não encontrada.")
            idx_inicial = idx_inicial[0]
        
            # Valor inicial no dia do aporte
            df.loc[idx_inicial, 'valor_simulado'] = self.dfs_movement_history[fund_name]['valor_inicial']
        
            for i in range(idx_inicial + 1, len(df)):
                dia = df.loc[i, 'date']
                anterior = df.loc[i - 1, 'valor_simulado']
        
                if pd.isnull(anterior):
                    continue
        
                # Ajuste de aportes e resgates ANTES da valorização
                aporte = aportes_dict.get(dia, 0)
                resgate = resgates_dict.get(dia, 0)
                base = anterior + aporte - resgate
        
                # Aplica a rentabilidade do dia
                pct = df.loc[i, 'quota_pct_change']
                if pd.notnull(pct):
                    df.loc[i, 'valor_simulado'] = base * (1 + pct)
                else:
                    df.loc[i, 'valor_simulado'] = base
            
            self.quota_dfs[fund_name] = df
            
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
        self.calculate_quota_variation()
        self.calculate_role_period_rentability()   
        self.calculate_1m_3m_6m_12m_24m_rentability()
        #fazer os gráficos dos períodos

if __name__ == '__main__':
    temp = FundRentabilityCalculator()
    temp.run()
