
## Project title: *An Automated system for local GPs*

### Student name: *Om Vilas Shimpi*

### Student email: *ovs1@student.le.ac.uk*

### Project description: 
*The healthcare industry suffers from inefficiencies in appointment scheduling and prescription management. This project intends to provide a safe and intelligent web-based solution for local GP surgeries that will improve patient-doctor relations. Patients may easily schedule appointments, manage medications, prescriptions and receive automated reminders, while doctors can update their availability in real time. The platform emphasizes data security, accessibility, and user experience to ensure compliance with healthcare standards. Using modern online technologies, this solution intends to streamline operations, minimize administrative burden, and increase patient interaction.*

### List of requirements (objectives): 


Essential (Core Features - Minimum Viable Product)

- Secure user authentication for patients, doctors, pharmacists and admin.
- Appointment booking system allowing patients to check and book available slots.
- Doctors availability management (add, update schedules).
- Prescription management.
	- Doctors will prescribe the medicine and will sent the prescription to the selected Pharmacy of the Patient through which Patient could buy and get the medicine from there.
	- Patients can view their active prescription.


Desirable (Enhancing Usability & Features)

- Implement Payment System for Pharmacy.
	- Patients can pay online to that pharmacy. 
- Automated reminders. 
 	- Notify in the form of Emails for upcoming appointments.
- Search & filtering. 		
 	- Searching can be done to find the nearest GP and Pharmacy as well.
 	- Searching and Filtering can be done by Doctors and Pharmacists to sort out the medicines.
- Mobile-friendly UI for accessibility on different devices.

Optional (Advanced & Research-Oriented Features)
- AI-Powered Chatbot for Instant Patient Assistance.
	- Can solve general problems of the patients and suggest them medicines accordingly, if not then will suggest to go and see a doctor.
- Multi-language support – Provide support for multiple languages to enhance accessibility for diverse user demographics.


Technology Stack
- Frontend - Angular
- Backend - Python
- Database - MySQL

##  Installation & Setup Requirements

To run this project, make sure to follow the steps below to set up your environment correctly.

###  Python Dependencies

Install all required Python libraries:

pip install flask, flask-cors, flask-mail, flask-mysqldb, flask-sqlalchemy, mysql-connector-python, bcrypt, pyjwt, fpdf, stripe, apscheduler

### MySQL Setup
- Install MySQL Server (e.g., MySQL Community Edition).
- CREATE DATABASE local_gp_system;
- Ensure these credentials are correct in config.py:
	- "user": "YOUR_USERNAME_HERE",
	- "password": "YOUR_PASSWORD_HERE",
	- "database": "local_gp_system"

### Angular Frontend Setup
- Install Node.js and Angular CLI: npm install -g @angular/cli
- Navigate to your Angular frontend directory and run the app: 
	- npm install
	- ng serve
The app will run at: http://localhost:4200

### Gmail Configuration (Flask-Mail)
- Use a Gmail account.
- Enable 2-Step Verification.
- Create an App Password.
- Update config.py:
	- MAIL_USERNAME = "your_email@gmail.com"
	- MAIL_PASSWORD = "your_app_password"

### Stripe Configuration
- Create a Stripe account at: https://dashboard.stripe.com
- Get your test secret key.
- Update config.py:
	- STRIPE_SECRET_KEY = "your_test_secret_key"


