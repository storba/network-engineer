FROM python:3.12-alpine
RUN pip install --no-cache-dir pyyaml
COPY apply.py /apply.py
ENTRYPOINT ["python", "/apply.py"]
