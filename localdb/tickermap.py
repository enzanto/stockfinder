#third party
from sqlalchemy import Column, JSON, String
from sqlalchemy.orm import sessionmaker,declarative_base

import settings

Base = declarative_base()
class TickerMap:
    class jsonMap(Base):
        __tablename__ = 'tickermap'
        ticker = Column(String, primary_key=True)
        json_data = Column(JSON)

    def __init__(self):
        # self.engine=create_engine(settings.db_connect_address)
        self.engine = settings.engine
        Base.metadata.create_all(self.engine)
    def insert_map_data(self,ticker, json_data):
        with sessionmaker(bind=self.engine)() as session:
            record = self.session.query(self.jsonMap).filter_by(ticker=ticker.lower()).first()
            if record:
                record.json_data = json_data
            else:
                new_record = self.jsonMap(ticker=ticker.lower(), json_data=json_data)
                session.add(new_record)
            session.commit()
    def get_map_data(self,ticker):
        with sessionmaker(bind=self.engine)() as session:
            record = session.query(self.jsonMap).filter_by(ticker=ticker).first()
            if record:
                return record.json_data
            else:
                return None