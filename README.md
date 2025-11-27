
# 🏥 MediServe  
**MediServe** is a **community health portal** designed to support barangay residents — particularly **senior citizens, PWDs, and low-income households** — by streamlining access to **free medicines** and health information.  
It enables residents to conveniently request medicines online and track delivery updates, while health center staff manage inventory, requests, and announcements through an integrated system.

---

## ✨ Features

### 👨‍👩‍👧‍👦 User Portal (Barangay Residents)
- 💊 **Medicine Catalog** – Browse available medicines with real-time stock status (In Stock, Low Stock, Out of Stock).  
- 📦 **Free Medicine Requests** – Request available medicines online at no cost.  
- 🚚 **Delivery Tracking** – Track the status of your medicine request from processing to delivery.  
- 👤 **Profile & History** – View and edit your personal details and see your request history.  
- 📢 **Announcements** – Stay informed about health advisories, vaccine drives, and barangay health programs.

---

### 🧑‍⚕️ Admin Portal (Health Center Staff)
- 📊 **Admin Dashboard** – Centralized hub for managing medicine inventory and user requests.  
- 📦 **Inventory Management** – Add, update, and monitor medicine stocks with color-coded alerts.  
- 🧾 **Request Management** – Review incoming medicine requests, update statuses, and mark deliveries as completed.   
- 📢 **Announcement Posting** – Publish important community health updates.

---

## 🛠️ Tech Stack
| Layer | Technology |
|--------|-------------|
| **Frontend** | Django Templates, HTML, CSS, JavaScript |
| **Backend** | Django (Python) |
| **Database** | Supabase (PostgreSQL) |
| **Version Control & Collaboration** | Git + GitHub |

---

## ⚙️ Setup & Run Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/veinP/CSIT327-G5-MediServe.git
cd CSIT327-G5-MediServe
````

---

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate the environment:

* **Windows:**

  ```bash
  venv\Scripts\activate
  ```
* **macOS/Linux:**

  ```bash
  source venv/bin/activate
  ```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Connect to the Database via Supabase

1. Log in to your **Supabase** account.
2. Open your MediServe project → click **“Connect”** at the top → scroll to **Session pooler**.
3. Copy the **PostgreSQL connection string** (it looks like this):

   ```
   postgresql://postgres:[YOUR_PASSWORD]@db.[your-supabase-id].supabase.co:6543/postgres
   ```
4. Create a file named `.env` in the project root (same folder as `manage.py`).
5. Paste the following inside your `.env` file:

   ```
   DATABASE_URL=postgresql://postgres:[YOUR_PASSWORD]@db.[your-supabase-id].supabase.co:6543/postgres
   ```
6. Save the file.

⚠️ **Important:** Do **not** commit `.env` to GitHub.

---

### 5. Apply Database Migrations

Once your Supabase `.env` is configured, run:

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### 6. Run the Development Server

Start the local Django server:

```bash
python manage.py runserver
```

Then open this link in your browser:
👉 https://csit327-g5-mediserve.onrender.com/accounts/login/

---

## 👨‍💻👩‍💻 Team Members

| Name                         | Role           | Email                                                                     | Github Usernames      |
| ---------------------------- | -------------- | ------------------------------------------------------------------------- | ----------------------|
| **Vein Carmell Pangilinan**  | Lead Developer | [veincarmell.pangilinan@cit.edu](mailto:veincarmell.pangilinan@cit.edu)   | veinP                 |  
| **Franklyn John Panugaling** | Developer      | [franklynjohn.panugaling@cit.edu](mailto:franklynjohn.panugaling@cit.edu) | frnks1                |
| **Kristine Eunice Pureza**   | Developer      | [kristineeunice.pureza@cit.edu](mailto:kristineeunice.pureza@cit.edu)     | kristineeunicepureza  |                |
| **USER 3**                   | Developer      | [kristineeunice.pureza@cit.edu](mailto:kristineeunice.pureza@cit.edu)     |                       |

