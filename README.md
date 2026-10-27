# Hotel Management System with Face Recognition Check-in

A Django-based hotel management system designed to streamline hotel operations with booking management, customer management, room management, check-in/check-out workflows, reporting, and face recognition-assisted check-in.

## Overview

This project was developed as a graduation project with the goal of improving hotel check-in efficiency and reducing manual work.

The system combines traditional hotel management features with face recognition technology to support a more convenient and modern guest check-in process.

## Features

- User authentication and account management
- Hotel room management
- Customer management
- Booking management
- Online booking requests
- Check-in workflow
- Face recognition-assisted check-in
- Check-out workflow
- Customer portal
- Administrative dashboard
- Reports and hotel operation statistics
- Responsive web interface

## Tech Stack

### Backend
- Python
- Django

### Frontend
- HTML
- CSS
- JavaScript
- Django Templates

### Database
- SQLite for local development

### Computer Vision
- Face recognition functionality
- Image processing for guest identification

## Project Structure

```text
hotel_face_checkin/
├── accounts/
├── bookings/
├── checkin/
├── checkout/
├── config/
├── customer_portal/
├── customers/
├── dashboard/
├── hotel_site/
├── reports/
├── rooms/
├── static/
├── templates/
├── manage.py
└── requirements.txt
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/thetai1102/hotel-management-system-with-face-recognition-check-in.git
```

### 2. Enter the project directory

```bash
cd hotel-management-system-with-face-recognition-check-in
```

### 3. Create a virtual environment

Windows:

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file or configure the required environment variables in your system.

Example:

```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
```

Do not commit real secrets or production credentials to GitHub.

### 6. Apply database migrations

```bash
python manage.py migrate
```

### 7. Create an administrator account

```bash
python manage.py createsuperuser
```

### 8. Run the development server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Environment Variables

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_DEBUG` | Enables or disables Django debug mode |

## Screenshots

Screenshots of the system will be added here.

Recommended screenshots:

- Login page
- Admin dashboard
- Booking management
- Customer management
- Room management
- Face recognition check-in
- Check-out page
- Reports dashboard

## Security

Sensitive files and local development data are excluded from version control, including:

- `.env`
- local SQLite databases
- virtual environments
- uploaded media
- Python cache files

## What I Learned

During the development of this project, I gained practical experience with:

- Django application architecture
- Database models and relationships
- Authentication and authorization
- CRUD operations
- Hotel booking workflows
- Check-in and check-out processes
- Integrating face recognition into a web application
- Managing environment variables and sensitive configuration
- Git and GitHub version control
- Structuring a multi-module Django project

## Future Improvements

- Improve face recognition accuracy
- Add automated testing
- Add Docker support
- Deploy the application to a cloud platform
- Add PostgreSQL support for production
- Improve UI/UX
- Add email notifications
- Add online payment support
- Add CI/CD workflows
- Improve reporting and analytics

## Author

**The Tai**

GitHub: [@thetai1102](https://github.com/thetai1102)

## License

This project is intended for educational and portfolio purposes.
