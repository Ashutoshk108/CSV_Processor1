import os
from dotenv import load_dotenv
from celery import Celery
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.models import Product, Base
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from redis import Redis, ConnectionPool
import requests

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
    secure=True,
)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

redis_pool = ConnectionPool.from_url(REDIS_URL, max_connections=10, decode_responses=True)
redis_client = Redis(connection_pool=redis_pool)

celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

# Function to check Redis connection before processing
def check_redis_connection():
    try:
        if not redis_client.ping():
            raise ConnectionError("Redis connection failed")
    except Exception as e:
        raise ConnectionError(f"Redis connection error: {e}")

@celery_app.task(bind=True, max_retries=3)
def process_images(self, request_id, webhook_url):
    """Process images and update the database"""
    
    # Ensure Redis connection is alive
    check_redis_connection()
    
    db = SessionLocal()
    try:
        # Cache task status in Redis
        cache_key = f"task_status:{request_id}"
        redis_client.set(cache_key, "processing", ex=600)

        result = []
        products = db.query(Product).filter(Product.request_id == request_id).all()
        for product in products:
            input_urls = product.input_image_urls
            print(f"input_urls_from_db: {input_urls}")
            output_urls = []
            for url in input_urls:
                upload_result = cloudinary.uploader.upload(url, quality="50")
                print(f"uploaded {url} to {upload_result}")
                output_urls.append(upload_result["secure_url"])
            product.output_image_urls = output_urls
            result.append(
                {
                    "serial_number": product.serial_number,
                    "product_name": product.product_name,
                    "input_urls": input_urls,
                    "output_urls": output_urls,
                }
            )
            product.processed = True
            db.commit()

        webhook_payload = {
            "request_id": request_id,
            "status": "completed",
            "output": result,
        }
        response = requests.post(webhook_url, json=webhook_payload)
        print(f"Webhook response: {response.status_code}, {response.text}")

    except Exception as e:
        db.rollback()
        print(f"Error processing images: {e}")
    finally:
        db.close()
