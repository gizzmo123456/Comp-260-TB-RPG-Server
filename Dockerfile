# SERVER LOBBIES
# server_lobbies.0.1.2
######################

FROM python:3.7.7-alpine3.11

WORKDIR /usr/src/app

ENV PYTHONPATH "${PYTHONPATH}:/usr/src/app"

COPY py_requirements.txt ./
RUN pip install --no-cache-dir -r py_requirements.txt

COPY ./server_lobbies.py ./
COPY ./Common/ ./Common/
COPY ./Sockets/ ./Sockets/

CMD [ "python", "-u", "./server_lobbies.py" ]