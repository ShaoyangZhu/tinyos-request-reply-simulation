FROM ucmercedandeslab/tinyos:tossim

WORKDIR /app

COPY . /app

ENTRYPOINT ["sh", "/app/container/run-scenario.sh"]
CMD ["baseline"]
