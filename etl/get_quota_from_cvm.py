from dataclasses import dataclass,field
from typing import Union
from datetime import datetime,timedelta
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from io import StringIO
import traceback
import pandas as pd
import time
import json

ROOT_DIR = Path(__file__).resolve().parent.parent
FUNDS_PATH = ROOT_DIR / "config" / "funds.json"

def generate_historical_period_list(start: str) -> list[str]:
    end = datetime.today().strftime('%m/%Y')
    datas = pd.date_range(start=start, end=end, freq='MS')
    return [data.strftime('%m/%Y') for data in datas]

def get_last_month_date() -> list[str]:
    tday = datetime.today()
    first_day_of_this_month = tday.replace(day=1)
    last_month = first_day_of_this_month - timedelta(days=1)
    return [last_month.strftime('%m/%Y')]

@dataclass
class GetFundoQuotaFromCVM():
    historical: Union[bool,str] = False
    last_month: bool = True
    month_list: list = field(default_factory=list)

    def get_historical_months_list(self):
        if self.historical:
            self.period_list = generate_historical_period_list(self.historical)
            
        elif self.last_month:
            self.period_list = get_last_month_date()
        else:
            self.period_list = self.month_list     

    def import_fund_quota_cvm(self):
        with open(FUNDS_PATH, 'r', encoding='utf-8') as f:
            funds_ws_path = json.load(f)
        
        self.df_funds_ws_path = pd.DataFrame(funds_ws_path)
        
    def _navigate_to_fund(self, browser: webdriver, url_fund: str):
        url = 'https://cvmweb.cvm.gov.br/SWB/Sistemas/SCW/CPublica/FormBuscaPartic.aspx?TpConsulta=3'
        browser.get(url)
        time.sleep(1)
        browser.get(url_fund)

    def _select_month(self, browser: webdriver, month: str):
        try:
            wait = WebDriverWait(browser, 10)
            select_elem = wait.until(EC.presence_of_element_located((By.NAME, "ddComptc")))
            select = Select(select_elem)
            select.select_by_visible_text(month)
        except Exception as e:
            raise RuntimeError(f"Unable to find/select date {month}: {e}")

    def _parse_table(self, html:str, fund: str, month:str) -> pd.DataFrame:
        try:
            tables = pd.read_html(StringIO(html), header=0, decimal=',', thousands='.')
            df = tables[1]
            df = df[df['Quota (R$)'].notna()]
            df = df.rename(columns={
                'Dia': 'date',
                'Quota (R$)': 'quota',
                'Captação no Dia (R$)': 'aum_in',
                'Resgate no Dia (R$)': 'aum_out',
                'Patrimônio Líquido (R$)': 'aum',
                'N°. Total de Cotistas': 'shareholders'
            })
            df['date'] = df['date'].astype(str) + '/' + month
            df['date'] = df['date'].apply(lambda x: datetime.strptime(x, '%d/%m/%Y').strftime('%Y-%m-%d'))
            df['fund'] = fund
            df = df.drop(columns=['Total da Carteira (R$)', 'Data da próxima informação do PL'], errors='ignore')
            return df
        except Exception as e:
            raise RuntimeError(f"Error while parsing table of fund {fund} ({month}): {e}")

    def _save_df(self, df: pd.DataFrame, fund: str, month: str):
        temp_month = month.replace('/', '')
        path = ROOT_DIR / "data" / "raw" / f"{fund}_{temp_month}.xlsx"
        df.to_excel(path, index=False)

    def get_and_save_funds_quota(self):
        browser = webdriver.Chrome()
        try:
            for row in self.df_funds_ws_path.itertuples():
                self._process_fund(browser, row)
        finally:
            browser.quit()

    def _process_fund(self, browser: webdriver.Chrome, row):
        fund = row.fund_name
        url_fund = row.url_cvm
    
        try:
            self._navigate_to_fund(browser, url_fund)
        except Exception as e:
            print(f"Error while connecting with {fund} website: {e}")
            return
    
        for month in self.period_list:
            self._process_fund_month(browser, fund, month)
    
    def _process_fund_month(self, browser: webdriver.Chrome, fund: str, month: str):
        try:
            self._select_month(browser, month)
            time.sleep(2)
            html = browser.page_source
            df = self._parse_table(html, fund, month)
            if not df.empty:
                self._save_df(df, fund, month)
            print(f"✔  {month} Collected: {fund}", flush=True)
        except Exception as e:
            print(f"Error while processing {fund} data ({month}): {e}")

    def run(self):
        self.get_historical_months_list()
        self.import_fund_quota_cvm()
        self.get_and_save_funds_quota()

if __name__ == '__main__':
    temp = GetFundoQuotaFromCVM(historical='2025/05')
    temp.run()