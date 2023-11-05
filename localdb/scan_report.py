
from sqlalchemy import Column, JSON, String, DateTime, LargeBinary
from sqlalchemy.orm import sessionmaker,declarative_base
from sqlalchemy.types import TypeDecorator

from datetime import datetime
import settings

tz = settings.tz
Base = declarative_base()
class AwareDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
class ScanReport:
    class report(Base):
        __tablename__ = 'report_test2'
        ticker = Column(String, primary_key=True)
        date_col = Column(DateTime, AwareDateTime(timezone=True), name="date")
        json_data = Column(JSON)
        investtech = Column(LargeBinary)
        pivots = Column(LargeBinary)

    def __init__(self):
        # self.engine=create_engine(settings.db_connect_address)
        self.engine = settings.engine
        Base.metadata.create_all(self.engine)


    def insert_report_data(self,ticker, json_data, image, investtech_img = None):
        with sessionmaker(bind=self.engine)() as session:
            record = session.query(self.report).filter_by(ticker=ticker).first()
            if record:
                record.json_data = json_data
                record.date_col = datetime.now(tz)
                record.investtech = investtech_img
                record.pivots = image
            else:
                new_record = self.report(ticker=ticker, json_data=json_data, date_col=datetime.now(tz), investtech=investtech_img, pivots=image)
                session.add(new_record)
            session.commit()
    def get_report_data(self, ticker):
        with sessionmaker(bind=self.engine)() as session:
            record = session.query(self.report).filter_by(ticker=ticker).first()
            if record:
                return record.date_col, record.json_data, record.investtech, record.pivots
            else:
                return None, None, None, None
