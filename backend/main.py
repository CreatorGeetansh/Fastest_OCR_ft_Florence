import torch
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoModelForCausalLM, AutoProcessor
from PIL import Image
import io
import time
import uuid
import os
from dotenv import load_dotenv

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Load environment variables from .env file
load_dotenv()

# Import our configured logger and request_id context variable
from logging_config import logger, request_id_var

# --- 1. Load Model and Processor ---
logger.info("Starting server...")
logger.info("Loading environment variables and model...")

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")
logger.info(f"Using device: {device}")

try:
    model = AutoModelForCausalLM.from_pretrained(
        "Geetansh13/Florence-2-FT-DocVQA", 
        trust_remote_code=True
    ).to(device)

    processor = AutoProcessor.from_pretrained(
        "Geetansh13/Florence-2-FT-DocVQA", 
        trust_remote_code=True
    )
    logger.info("Model and processor loaded successfully!")
except Exception as e:
    logger.critical(f"Failed to load model: {e}", exc_info=True)
    # Exit if model fails to load, as the app is useless without it
    exit()


# --- 2. Create FastAPI App ---
app = FastAPI(title="Florence-2 DocVQA API")

# --- 3. Add Middleware (Logging, CORS) ---

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    Middleware to log requests and inject a unique request_id.
    """
    # Generate a unique ID for the request
    req_id = str(uuid.uuid4())
    request_id_var.set(req_id) # Set the request_id in the context

    start_time = time.time()
    
    logger.info(f"Request started: {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = req_id
        logger.info(
            f"Request finished: {response.status_code} "
            f"| Processed in {process_time:.4f}s"
        )
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {e} | Processed in {process_time:.4f}s",
            exc_info=True # This will log the full traceback
        )
        # Re-raise the exception to let FastAPI's default error handling work
        raise e

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 4. Define the Inference Function ---

def run_inference(image: Image.Image, question: str):
    task_prompt = "<DocVQA>"
    prompt = task_prompt + question

    if image.mode != "RGB":
        logger.debug("Image mode is not RGB, converting...")
        image = image.convert("RGB")
    
    try:
        logger.debug("Preprocessing inputs for the model...")
        inputs = processor(text=prompt, images=image, return_tensors="pt").to(device)
        
        logger.debug("Generating output from the model...")
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            num_beams=3,
            early_stopping=True,
        )
        
        logger.debug("Decoding generated IDs...")
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        
        logger.debug("Post-processing the generated text...")
        parsed_answer = processor.post_process_generation(
            generated_text, 
            task=task_prompt, 
            image_size=(image.width, image.height)
        )
        
        answer = parsed_answer.get("DocVQA", "Could not parse answer.")
        logger.info(f"Inference successful. Answer found: '{answer[:50]}...'")
        return answer

    except Exception as e:
        logger.error(f"An error occurred during inference: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

# --- 5. Define the API Endpoint ---

@app.post("/api/process")
async def process_image_and_question(
    file: UploadFile = File(...), 
    question: str = Form(...)
):
    logger.info(f"Received new request: filename='{file.filename}', question='{question}'")
    
    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents))
        logger.debug(f"Image '{file.filename}' opened successfully.")
    except Exception:
        logger.warning(f"Invalid image file uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="Invalid image file provided.")

    answer = run_inference(image, question)
    
    if device == "cuda":
        torch.cuda.empty_cache()
        logger.debug("CUDA cache cleared.")
        
    return {"answer": answer}

# --- 6. Add a Root Endpoint for Health Check ---

@app.get("/")
def read_root():
    logger.info("Health check endpoint was hit.")
    return {"status": "Florence-2 API is running"}