from dataclasses import dataclass,field
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime
import pandas as pd
import time
import sys

@dataclass
class GetFundoQuotaFromCVM():
    historical: bool = False
    last_month: bool = True
    month_list: list = field(default_factory=list)

    def get_historical_months_list(self):
        if self.historical:
            pass
            #get historical months list
            #save it to a main list of dates
        elif self.last_month:
            pass
            #get last month
        else:
            pass
            #set month list arg
        

    def import_fund_quota_cvm(self):
        pass

    def run(self):
        self.get_historical_months_list()
        self.import_fund_quota_cvm()

if __name__ == '__main__':
    temp = GetFundoQuotaFromCVM()
    temp.run()
