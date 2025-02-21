from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from app.tasks import process_images
from app.models import Product, get_db
from app.validate import validate_csv
import cloudinary
import cloudinary.uploader
import csv
import uuid
import os
from dotenv import load_dotenv
import logging
import uvicorn

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cloudinary Configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

@app.post("/upload/")
async def upload_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db), webhook_url: str = Form("")):
    
    contents = await file.read()
    validate_csv(contents.decode())
    csv_data = csv.reader(contents.decode().splitlines())
    next(csv_data)  # Skip header
    
    try:
        request_id = str(uuid.uuid4())
        for row in csv_data:
            try:
                serial_number, product_name, input_image_urls = row
                input_image_urls_list = input_image_urls.split(',')
                product = Product(
                    serial_number=serial_number,
                    product_name=product_name,
                    input_image_urls=input_image_urls_list,
                    request_id=request_id
                )
                db.add(product)
            except ValueError as e:
                logger.error(f"Error processing row {row}: {e}")
                raise HTTPException(status_code=400, detail="Invalid CSV format")
        db.commit()
        
        process_images.delay(request_id, webhook_url)
        return {"request_id": request_id}
    
    except Exception as e:
        print(f"Error processing CSV: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/status/{request_id}")
def check_status(request_id: str, db: Session = Depends(get_db)):
    """Checks the processing status of the images."""
    
    product = db.query(Product).filter(Product.request_id == request_id).all()
    output_image_record = []
    processed = True
    
    for p in product:
        prod = {
            "serial_number": p.serial_number,
            "product_name": p.product_name,
            "output_image_urls": p.output_image_urls,
        }
        output_image_record.append(prod)
        
        if processed and not p.processed:
            processed = False

    if product:
        return {"processed": processed, "output": output_image_record}
    
    raise HTTPException(status_code=404, detail="Request ID not found")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
