FROM python:3.10-slim


WORKDIR /usr/src/app
ENV TZ=Europe/Oslo
#RUN python -m pip install --upgrade pip
COPY requirements.txt ./
run apt update && apt install pip --upgrade -y
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
#RUN cp crontab /etc/cron.d/stockfinder


CMD ["python", "./main.py"]