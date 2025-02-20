# Asynchronous Workers

## Overview
This project uses Celery for processing images in the background.  
Once a CSV file is uploaded, the processing task is queued using Celery.

## Worker Functions
### process_images(request_id: str, webhook_url: str)
- Fetches all products with `request_id`
- Calls an external image processing API
- Updates database with `output_image_urls`
- Sends a callback (webhook) to notify when processing is complete

## Running Celery Workers
To start the Celery worker, run:
celery -A tasks worker --loglevel=info
