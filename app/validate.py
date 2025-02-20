import csv
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from typing import List


EXPECTED_HEADERS = ["S. No.", "Product Name", "Input Image Urls"]

def validate_csv(contents: str):
    csv_data = csv.reader(contents.splitlines())
    headers = next(csv_data)

    if headers != EXPECTED_HEADERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CSV headers. Expected: {EXPECTED_HEADERS}, Found: {headers}"
        )

    rows = []
    for row_number, row in enumerate(csv_data, start=1):
        if len(row) != len(EXPECTED_HEADERS):
            raise HTTPException(
                status_code=400,
                detail=f"Row {row_number} has an incorrect number of columns."
            )

        serial_number, product_name, input_image_urls = row

        try:
            serial_number = int(serial_number)
            if serial_number <= 0:
                raise ValueError("Serial number must be positive.")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid serial number at row {row_number}. Must be a positive integer."
            )

        if not product_name.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Missing product name at row {row_number}."
            )

        if not input_image_urls:
            raise HTTPException(
                status_code=400,
                detail=f"Missing input image URLs at row {row_number}."
            )

        rows.append(row)

    return rows
