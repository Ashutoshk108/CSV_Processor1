# CSV Processor to process a csv file and reduce image size

## Features
- Upload CSV to store product data
- Background image processing using Celery
- Webhook for processing status updates

## Setup
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
celery -A tasks worker --loglevel=info
