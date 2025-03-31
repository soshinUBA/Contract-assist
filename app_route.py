from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import shutil
import os
import uuid
import csv
from typing import Optional, List, Dict
from pydantic import BaseModel
import uvicorn
from datetime import datetime
import asyncio

# Import your contract processing functions
from main_current_annonymizer import contract_assist 

app = FastAPI(
    title="Contract Assistant API",
    description="API for processing and analyzing contracts",
    version="1.0.0"
)

# Create necessary directories if they don't exist
os.makedirs("./uploads", exist_ok=True)
os.makedirs("./Output", exist_ok=True)
os.makedirs("./ExcelOutput", exist_ok=True)

# File to store tasks information
TASKS_CSV_FILE = "tasks.csv"
CSV_FIELDNAMES = ["task_id", "status", "created_at", "completed_at", "file_name", "output_file", "error"]

# In-memory task tracking
processing_tasks: Dict[str, any] = {}


class ProcessingStatus(BaseModel):
    task_id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    file_name: str
    output_file: Optional[str] = None
    error: Optional[str] = None


def initialize_tasks_csv():
    """Initialize the CSV file if it doesn't exist or is empty"""
    create_file = not os.path.exists(TASKS_CSV_FILE) or os.path.getsize(TASKS_CSV_FILE) == 0
    
    if create_file:
        with open(TASKS_CSV_FILE, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()


def load_tasks_from_csv():
    """Load tasks from CSV file into memory"""
    if not os.path.exists(TASKS_CSV_FILE):
        initialize_tasks_csv()
        return
    
    with open(TASKS_CSV_FILE, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Convert row to ProcessingStatus object
            task_status = ProcessingStatus(**row)
            processing_tasks[row['task_id']] = task_status


def save_task_to_csv(task: ProcessingStatus):
    """Save or update a task in the CSV file"""
    # Read existing tasks
    existing_tasks = []
    if os.path.exists(TASKS_CSV_FILE):
        with open(TASKS_CSV_FILE, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            existing_tasks = [row for row in reader if row['task_id'] != task.task_id]
    
    # Append the new/updated task
    with open(TASKS_CSV_FILE, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        
        # Write existing tasks (except the one being updated)
        for existing_task in existing_tasks:
            writer.writerow(existing_task)
        
        # Write the updated task
        writer.writerow(task.dict())


async def process_contract_task(task_id: str, file_path: str, original_filename: str):
    """Background task to process a contract"""
    try:
        # Update status to processing
        processing_tasks[task_id].status = "processing"
        save_task_to_csv(processing_tasks[task_id])
        
        # Offload processing to a separate thread
        loop = asyncio.get_event_loop()
        result_path = await loop.run_in_executor(None, contract_assist, file_path)
        
        if result_path and os.path.exists(result_path):
            processing_tasks[task_id].status = "completed"
            processing_tasks[task_id].output_file = result_path
            processing_tasks[task_id].completed_at = datetime.now().isoformat()
        else:
            processing_tasks[task_id].status = "failed"
            processing_tasks[task_id].error = "Processing failed or no output was generated"
            processing_tasks[task_id].completed_at = datetime.now().isoformat()
            
    except Exception as e:
        processing_tasks[task_id].status = "failed"
        processing_tasks[task_id].error = str(e)
        processing_tasks[task_id].completed_at = datetime.now().isoformat()
    
    # Save updated status to CSV
    save_task_to_csv(processing_tasks[task_id])


@app.post("/contracts/process", response_model=ProcessingStatus, summary="Process a contract")
async def process_contract(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload a contract PDF for processing.
    
    Returns a task ID that can be used to check the status of the processing.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Generate a unique ID for this task
    task_id = str(uuid.uuid4())
    
    # Save the uploaded file
    file_path = f"./uploads/{task_id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create a status entry for this task
    task_status = ProcessingStatus(
        task_id=task_id,
        status="queued",
        created_at=datetime.now().isoformat(),
        file_name=file.filename
    )
    processing_tasks[task_id] = task_status
    
    # Save to CSV
    save_task_to_csv(task_status)
    
    # Start processing in the background
    background_tasks.add_task(process_contract_task, task_id, file_path, file.filename)
    
    return task_status


@app.get("/contracts/status/{task_id}", response_model=ProcessingStatus, summary="Check processing status")
async def check_status(task_id: str):
    """
    Check the status of a contract processing task.
    """
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return processing_tasks[task_id]


@app.get("/contracts/download/{task_id}", summary="Download processed results")
async def download_results(task_id: str):
    """
    Download the Excel results file for a completed processing task.
    """
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = processing_tasks[task_id]
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed. Current status: {task.status}")
    
    if not task.output_file or not os.path.exists(task.output_file):
        raise HTTPException(status_code=404, detail="Output file not found")
    
    return FileResponse(
        path=task.output_file,
        filename=os.path.basename(task.output_file),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.on_event("startup")
async def startup_event():
    """Initialize data on startup"""
    # Initialize and load tasks from CSV
    initialize_tasks_csv()
    load_tasks_from_csv()


@app.get("/", summary="API root")
async def root():
    """
    Root endpoint with basic API information.
    """
    return {
        "name": "Contract Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "POST /contracts/process": "Upload and process a contract",
            "GET /contracts/status/{task_id}": "Check processing status",
            "GET /contracts/download/{task_id}": "Download processing results",
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)