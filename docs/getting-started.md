# Getting Started

## Prerequisites
- Python 3.10+ for the backend and pipeline scripts
- Node.js 18+ for the frontend
- A running backend API at `http://localhost:8000`

## Local Setup
1. Create and activate your Python virtual environment.
2. Install Python dependencies from `requirements.txt`.
3. Install frontend dependencies in `frontend/`.
4. Copy `.env.example` to `.env` where needed and set local API values.

## Run the App
- Start the backend API.
- Start the frontend dev server from `frontend/`.
- Open the frontend in the browser and confirm stock data loads.

## Build Checks
- Use `npm run build` in `frontend/` before publishing UI changes.
- Run the pipeline scripts in `src/` only when refreshing the model outputs.
