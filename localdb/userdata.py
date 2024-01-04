
from sqlalchemy import create_engine, Column, Integer, JSON, BigInteger, String, DateTime, LargeBinary
from sqlalchemy.orm import sessionmaker,declarative_base

import settings
Base=declarative_base()
class UserData:
    class UserData(Base):
        __tablename__ = 'userdata'
        userid = Column(BigInteger, primary_key=True)
        json_data = Column(JSON)

    def __init__(self):
        # engine=create_engine(settings.db_connect_address)
        engine = settings.engine
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session=Session()
    def get_userids(self):
        '''
        Returns a list of discord user ID's stored in DB

        :params return: list of ID's
        '''
        tuple_list = self.session.query(self.UserData.json_data).all()
        json_list = []
        for row in tuple_list:
            json_data = row[0]
            json_list.append(json_data)
        return json_list 
    def insert_portfolio_data(self,userid, json_data):
        '''
        Insert or update data on portfolio and/or watchlist

        :params userid: Discord user ID
        :params json_data: Json formatted data, required keys: userid, portfolio, watchlist
        '''
        required_keys = ['userid', 'portfolio','watchlist']
        for key in required_keys:
            if key not in json_data:
                json_data[key] = None
        record = self.session.query(self.UserData).filter_by(userid=userid).first()
        if record:
            record.json_data = json_data
        else:
            new_record = self.UserData(userid=userid, json_data=json_data)
            self.session.add(new_record)
        self.session.commit()
    def get_portfolio_data(self,userid):
        '''
        Fetches userdata with watchlist and portfolio from DB

        :params userid: Discord user ID
        :params return: Returns JSON formatted info, if not found returns None
        '''
        record = self.session.query(self.UserData).filter_by(userid=userid).first()
        if record:
            return record.json_data
        else:
            return None