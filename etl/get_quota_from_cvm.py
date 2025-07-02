from dataclasses import dataclass,field
from typing import Union
from datetime import datetime,timedelta
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import pandas as pd
import time
import sys
import json

ROOT_DIR = Path(__file__).resolve().parent.parent
FUNDS_PATH = ROOT_DIR / "config" / "funds.json"

def generate_historical_period_list(start: str) -> list[str]:
    end = datetime.today().strftime('%m/%Y')
    datas = pd.date_range(start=start, end=end, freq='MS')
    return [data.strftime('%m/%Y') for data in datas]

def get_last_month_date() -> str:
    tday = datetime.today()
    first_day_of_this_month = tday.replace(day=1)
    last_month = first_day_of_this_month - timedelta(days=1)
    return last_month.strftime('%m/%Y')

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
        
    def get_and_save_funds_quota(self):
        for row in self.df_funds_ws_path.itertuples():

            browser = webdriver.Chrome()
            print(browser.capabilities.get("chrome", {}).get("chromedriverVersion"))
            fund = row.fund_name
            url_fund = row.url_cvm
        
            url = 'https://cvmweb.cvm.gov.br/SWB/Sistemas/SCW/CPublica/FormBuscaPartic.aspx?TpConsulta=3'
            browser.get(url)
            WebDriverWait(browser, 1)
            time.sleep(1)
            browser.get(url_fund)
        
            for month in self.period_list:            
                # try:
                time.sleep(3)
                browser.find_element("xpath","//select[@name='ddComptc']/option[text()='" + month + "']").click()
                time.sleep(3)
                source = browser.page_source
                tables = pd.read_html(source, header = 0, decimal=',', thousands='.')[1]
                if len(tables) == 0:
                    continue
                tables = tables[tables['Quota (R$)'].notna()]
                tables = tables.rename(columns={'Dia' : 'date','Quota (R$)': 'quota', 'Captação no Dia (R$)' : 'aum_in','Resgate no Dia (R$)' : 'aum_out','Patrimônio Líquido (R$)':'aum','N°. Total de Cotistas' : 'shareholders'})
                del tables['Total da Carteira (R$)']
                del tables['Data da próxima informação do PL']
                tables['date']=tables['date'].astype(str)+'/'+month
                tables['date']=tables['date'].apply(lambda x: datetime.strptime(str(x), '%d/%m/%Y').strftime('%Y-%m-%d'))
                tables['fund'] = fund
                
                temp_month = month.replace('/','')
                tables.to_excel(rf"{ROOT_DIR}\data\raw\{fund}_{temp_month}.xlsx",index=False)
                    
                # except:
                #     print('error for the month')
        
            sys.stdout.write('\r' + 'got fund data from cvm: ' + fund)
            browser.close()

    def run(self):
        self.get_historical_months_list()
        self.import_fund_quota_cvm()
        self.get_and_save_funds_quota()

if __name__ == '__main__':
    temp = GetFundoQuotaFromCVM(historical='2025/05')
    temp.run()
