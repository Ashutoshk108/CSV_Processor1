import os
import threading
import requests
from dotenv import load_dotenv
from celery import Celery
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.models import Product
import cloudinary
import cloudinary.uploader
from kombu import pools

load_dotenv()

CLOUDAMQP_API_URL = os.getenv("RABBITMQ_URL", "pyamqp://guest@localhost//")  

# Cloudinary Config
cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
    secure=True,
)

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize Celery with RabbitMQ
celery_app = Celery(
    "tasks",
    broker=CLOUDAMQP_API_URL,
    backend="rpc://",
    broker_transport_options={
        "visibility_timeout": 3600,  
        "heartbeat": 30,  
        "confirm_publish": True, 
        "tcp_user_timeout": 10000,
        "socket_timeout": 5,  
    },
)

# Enable connection pooling
pools.set_limit(10) 

@celery_app.task(bind=True, max_retries=3)
def process_images(self, request_id, webhook_url):
    """Process images and update the database"""
    db = SessionLocal()
    try:
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
