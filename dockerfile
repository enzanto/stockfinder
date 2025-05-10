FROM python:3.12-slim


WORKDIR /usr/src/app
ENV TZ=Europe/Oslo
ENV LOGLEVEL=INFO
#RUN python -m pip install --upgrade pip
COPY requirements.txt ./
RUN apt update && apt install pip --upgrade -y
RUN apt-get update && apt-get install -y libxml2-dev libxslt1-dev
RUN pip install --no-cache-dir -r requirements.txt
RUN sed -i 's/import NaN/import nan/' /usr/local/lib/python3.12/site-packages/pandas_ta/momentum/squeeze_pro.py
COPY . .
#RUN cp crontab /etc/cron.d/stockfinder


CMD ["python", "./main.py"]
