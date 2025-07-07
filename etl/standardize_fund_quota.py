import os
import pandas as pd
from tqdm import tqdm
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = ROOT_DIR / "data" / "raw"
PROCESSED_DATA_PATH = ROOT_DIR / "data" / "processed"

class QuotaConsolidator():
    
    def __init__(self):
        pass

    def read_quota_history(self):
        self.quota_dfs = {}
        
        # Loop through files in the directory
        for filename in tqdm(os.listdir(RAW_DATA_PATH),'reading historic quota files'):
            if filename.endswith('.xlsx'):
                try:
                    filepath = os.path.join(RAW_DATA_PATH, filename)
                    df = pd.read_excel(filepath)
                    key = os.path.splitext(filename)[0]  # filename without extension
                    self.quota_dfs[key] = df
                except Exception as e:
                    print(f"Error while reading {filename}: {e}")
    
    def group_files_by_fund_name(self):
        self.quota_consolidated = {}
        
        for quota_key in tqdm(self.quota_dfs,'consolidating quota history'):
            try:
                fund_name = quota_key.split('_')[0]
            except Exception as e:
                print(f'name format is wrong: {e}')
                continue
            
            if fund_name not in self.quota_consolidated:
                self.quota_consolidated[fund_name] = pd.DataFrame()
            
            self.quota_consolidated[fund_name] = pd.concat([self.quota_consolidated[fund_name],self.quota_dfs[quota_key]])

    def export_consolidated_quota(self):
        for fund_name in self.quota_consolidated:
            self.quota_consolidated[fund_name] = self.quota_consolidated[fund_name].sort_values('date')
            self.quota_consolidated[fund_name].to_excel(rf"{PROCESSED_DATA_PATH}\{fund_name}_consolidated_quota.xlsx",index=False)

    def run(self):
        self.read_quota_history()
        self.group_files_by_fund_name()
        self.export_consolidated_quota()
        self.export_consolidated_quota()

if __name__ == '__main__':
    temp = QuotaConsolidator()
    temp.run()