from dataclasses import dataclass,field
from typing import Union
from datetime import datetime,timedelta
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import pandas as pd
import time
import sys

def generate_historical_period_list(start: str) -> list[str]:
    end = datetime.today().strftime('%Y/%m')
    datas = pd.date_range(start=start, end=end, freq='MS')
    return [data.strftime('%Y/%m') for data in datas]

def get_last_month_date() -> str:
    tday = datetime.today()
    first_day_of_this_month = tday.replace(day=1)
    last_month = first_day_of_this_month - timedelta(days=1)
    return last_month.strftime('%Y/%m')

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
        pass

    def run(self):
        self.get_historical_months_list()
        self.import_fund_quota_cvm()

if __name__ == '__main__':
    temp = GetFundoQuotaFromCVM(historical='2006/01')
    temp.run()
