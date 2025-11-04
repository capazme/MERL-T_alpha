#!/bin/bash

# RLCF Development Setup Script
# This script starts both the FastAPI backend and the React frontend

set -e

echo "🚀 Starting RLCF Framework Development Environment"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "requirements.txt" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: Please run this script from the RLCF root directory"
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
if ! command_exists python3; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

# Check Node.js
if ! command_exists node; then
    echo "❌ Error: Node.js is not installed"
    exit 1
fi

# Check npm
if ! command_exists npm; then
    echo "❌ Error: npm is not installed"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Created virtual environment"
fi

source venv/bin/activate
pip install -r requirements.txt
echo "✅ Python dependencies installed"

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
    echo "✅ Node.js dependencies installed"
else
    echo "✅ Node.js dependencies already installed"
fi
cd ..

# Create some demo data if database is empty
echo "🔧 Setting up demo data..."
python -c "
import sys
sys.path.append('.')
from rlcf_framework.database import engine
from rlcf_framework import models
import asyncio

async def create_demo_data():
    from sqlalchemy.ext.asyncio import AsyncSession
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    
    async with AsyncSession(engine) as db:
        # Check if we already have users
        from sqlalchemy import select
        result = await db.execute(select(models.User))
        users = result.scalars().all()
        
        if not users:
            # Create demo users
            demo_users = [
                models.User(username='admin', authority_score=0.95, track_record_score=0.9, baseline_credential_score=0.8),
                models.User(username='evaluator1', authority_score=0.75, track_record_score=0.7, baseline_credential_score=0.6),
                models.User(username='evaluator2', authority_score=0.65, track_record_score=0.6, baseline_credential_score=0.55),
                models.User(username='viewer', authority_score=0.3, track_record_score=0.2, baseline_credential_score=0.1),
            ]
            
            for user in demo_users:
                db.add(user)
            
            await db.commit()
            print('✅ Created demo users')
        else:
            print('✅ Demo users already exist')

asyncio.run(create_demo_data())
"

# Function to cleanup on exit
cleanup() {
    echo -e "\n🛑 Shutting down services..."
    if [ ! -z "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID"
        echo "✅ Backend stopped"
    fi
    if [ ! -z "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID"
        echo "✅ Frontend stopped"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start backend
echo "🔥 Starting FastAPI backend..."
source venv/bin/activate
uvicorn rlcf_framework.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
echo "✅ Backend started on http://127.0.0.1:8000 (PID: $BACKEND_PID)"

# Wait a moment for backend to start
sleep 3

# Start frontend
echo "🎨 Starting React frontend..."
cd frontend
npm run dev -- --host 127.0.0.1 --port 3000 &
FRONTEND_PID=$!
cd ..
echo "✅ Frontend started on http://127.0.0.1:3000 (PID: $FRONTEND_PID)"

echo ""
echo "🎉 RLCF Framework is now running!"
echo "=================================="
echo "• Frontend: http://127.0.0.1:3000"
echo "• Backend:  http://127.0.0.1:8000"
echo "• API Docs: http://127.0.0.1:8000/docs"
echo ""
echo "📝 Demo Users:"
echo "• admin (high authority)"
echo "• evaluator1 (medium authority)"  
echo "• evaluator2 (medium authority)"
echo "• viewer (low authority)"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for either process to exit
wait