
from sqlalchemy import Column, JSON, String, DateTime, LargeBinary
from sqlalchemy.orm import sessionmaker,declarative_base
from sqlalchemy.types import TypeDecorator

from datetime import datetime

import settings

tz = settings.tz
Base = declarative_base()
class AwareDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
class PortfolioReport:
    class report(Base):
        __tablename__ = 'portfolio_report'
        ticker = Column(String, primary_key=True)
        date_col = Column(DateTime, AwareDateTime(timezone=True), name="date")
        json_data = Column(JSON)
        investtech = Column(LargeBinary)
        pivots = Column(LargeBinary)

    def __init__(self):
        # engine=create_engine(settings.db_connect_address)
        engine = settings.engine
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session=Session()

    def insert_report_data(self,ticker, json_data, ):#image = None, investtech_img = None):
        '''
        Stores portfolio report data in DB
        
        :param ticker: Ticker symbol
        :param json_data: JSON formatted report data
        '''
        record = self.session.query(self.report).filter_by(ticker=ticker).first()
        if record:
            record.json_data = json_data
            record.date_col = datetime.now(tz)
            # record.investtech = investtech_img
            # record.pivots = image
        else:
            new_record = self.report(ticker=ticker, json_data=json_data, date_col=datetime.now(tz))#, investtech=investtech_img, pivots=image)
            self.session.add(new_record)
        self.session.commit()
    def get_report_data(self, ticker):
        '''
        Fetches report data and creation date from DB
        if no report is found, returns None for all params

        :param ticker: Ticker symbol
        :param return: Creation date, JSON formatted report
        '''
        record = self.session.query(self.report).filter_by(ticker=ticker).first()
        if record:
            return record.date_col, record.json_data#, record.investtech, record.pivots
        else:
            return None, None#, None, None