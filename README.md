# ⚙️ ByteLearn Backend

This repository contains the **FastAPI backend** for the ByteLearn application.  
It powers authentication, summaries, flashcards, quizzes, and all API features used by the frontend.

🔗 **Live App (Frontend):**  
https://bytelearn-frontend.vercel.app/

> The backend is deployed separately on **Render** and connected to the frontend.

---

## ✨ Features

- FastAPI backend with a modular project structure  
- User authentication with **OTP-based verification**  
- CRUD operations for core application models  
- **MySQL** database integration using **SQLAlchemy**  
- Database migrations with **Alembic**  
- Email sending via **Brevo**  
- Profile picture upload support  
- Fully deployed backend on **Render**

---

## 🛠️ Tech Stack

- FastAPI  
- Python  
- SQLAlchemy  
- MySQL  
- Alembic  
- Brevo (Email service)  
- Render (Deployment)

---

## ⚙️ Setup Instructions
```bash
1️⃣ Clone the Repository
git clone https://github.com/ByteLearn-Team/bytelearn-backend.git

2️⃣ Create .env File
Copy .env.example and configure the following:
Database URL
Brevo API Key
JWT Secret
Other required environment variables

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Run Database Migrations
alembic upgrade head

5️⃣ Start the Server
uvicorn app.main:app --reload

The local API will be available at:
http://127.0.0.1:8000
