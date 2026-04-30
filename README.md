# Timesheet & Comp-Off Management System

A Django-based web application for managing employee working hours on weekends/holidays and compensatory off (CompOff) tracking within a private organization network.

## Features

✅ **Employee Management**
- Add, edit, and manage employee records
- Track employee status (active/inactive)
- Search employees by name, ID, or email

✅ **Timesheet Management**
- Record weekend and holiday work dates
- Track work details with descriptions
- Filter timesheets by employee or type

✅ **Comp-Off Management**
- Create Comp-Off requests linked to work dates
- Update Comp-Off dates when employees take time off
- Track Comp-Off status (Pending, Approved, Taken, Cancelled)
- Optional notes for additional information

✅ **Built-in Admin Interface**
- Django Admin for managing all records
- User-friendly admin dashboard
- Bulk operations support

✅ **Authentication & Authorization**
- User registration and login system
- Password-based authentication
- Session management

✅ **Reporting**
- Employee-wise detailed reports
- Summary statistics
- Data filtering and export ready

## Project Structure

```
Timemaster automation/
├── manage.py                          # Django management script
├── requirements.txt                   # Python dependencies
├── README.md                          # This file
│
├── timemaster_project/                # Main project settings
│   ├── __init__.py
│   ├── settings.py                   # Django settings
│   ├── urls.py                       # URL routing
│   └── wsgi.py                       # WSGI configuration
│
├── timesheet/                         # Main Django app
│   ├── migrations/                   # Database migrations
│   ├── __init__.py
│   ├── admin.py                      # Admin interface configuration
│   ├── apps.py                       # App configuration
│   ├── forms.py                      # Django forms
│   ├── models.py                     # Database models
│   ├── urls.py                       # App URL routing
│   └── views.py                      # View logic
│
├── templates/                        # HTML templates
│   ├── base.html                     # Base template
│   ├── login.html                    # Login page
│   ├── register.html                 # Registration page
│   ├── dashboard.html                # Main dashboard
│   └── timesheet/                    # App-specific templates
│       ├── employee_form.html
│       ├── employee_list.html
│       ├── employee_report.html
│       ├── timesheet_form.html
│       ├── timesheet_list.html
│       ├── compoff_form.html
│       └── compoff_list.html
│
└── static/                           # Static files (CSS, JS, images)
    └── css/
```

## Database Models

### Employee
- **name**: Full name of employee
- **employee_id**: Unique employee ID (e.g., 001)
- **email**: Employee email address
- **department**: Department name
- **is_active**: Active status
- **created_date**: Record creation date
- **updated_date**: Last update date

### Timesheet
- **employee**: Foreign key to Employee
- **work_date**: Date when employee worked on weekend/holiday
- **day_type**: Type (WEEKEND or HOLIDAY)
- **description**: Additional details
- **created_date**: Record creation date
- **updated_date**: Last update date

### CompOff
- **employee**: Foreign key to Employee
- **timesheet**: Links to associated Timesheet record
- **compoff_date**: Date when Comp-Off will be/was taken (optional, can be updated later)
- **status**: Status (PENDING, TAKEN)
- **notes**: Additional notes
- **created_date**: Record creation date
- **updated_date**: Last update date

### Holiday
- **date**: Holiday/Weekend date
- **holiday_type**: Type (HOLIDAY, WEEKEND, SPECIAL)
  SPECIAL is holiday by SMBC and not allowed to and a mandatory day off.
- **description**: Holiday name/description
- **created_date**: Record creation date

## Installation & Setup

### 1. Prerequisites
- Python 3.8+
- pip (Python package manager)

### 2. Create Virtual Environment
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser (Admin Account)
```bash
python manage.py createsuperuser
```
Follow the prompts to create an admin username and password.

### 6. Run Development Server
```bash
python manage.py runserver 0.0.0.0:8000
```

The application will be available at:
- **Main Application**: http://localhost:8000/timesheet/
- **Admin Interface**: http://localhost:8000/admin/

## Usage

### First Time Setup

1. **Login**: Use the admin account created during setup
2. **Add Employees**: Navigate to "Employees" → "Add New Employee"
3. **Record Timesheets**: Go to "Timesheets" → "Add Timesheet" to record work dates
4. **Manage CompOffs**: Create Comp-Off entries and update them when employees take their time off
5. **View Reports**: Click on an employee to view their detailed report

### Regular Workflow

1. **Employee Works on Weekend/Holiday**
   - Navigate to Timesheets → Add Timesheet
   - Select employee and work date
   - Save the record

2. **Comp-Off Request**
   - Go to CompOffs → Add CompOff
   - Link to the corresponding timesheet
   - Status defaults to "PENDING"

3. **Update Comp-Off Status**
   - When Comp-Off is approved, update status to "APPROVED"
   - When employee takes it, update status to "TAKEN"
   - Can also add compoff_date at any time

4. **Generate Reports**
   - Click on employee name to view detailed report
   - Shows all timesheets and CompOffs for that employee
   - Useful for audits and analysis

## Admin Interface

Access the admin panel at `/admin/` with your superuser credentials.

### Admin Features:
- **Employee Management**: View, add, edit, delete employees
- **Timesheet Management**: Manage work records
- **Comp-Off Management**: Update Comp-Off details and status
- **Holiday Management**: Maintain holiday calendar
- **User Management**: Set admin privileges

### Filters & Search:
- Filter timesheets by date, employee, or type
- Search employees by name or ID
- Filter CompOffs by status or employee
- Advanced filtering available in admin interface

## Security Notes

⚠️ **Important for Production Deployment**:

1. **Change SECRET_KEY** in `settings.py`
   - Generate a new secure key using `django-insecure-key-generator`
   - Never commit the actual secret key to version control

2. **Set DEBUG = False** in production
   - Prevents sensitive error information from being displayed

3. **Configure ALLOWED_HOSTS**
   - Set to specific domain/IP addresses instead of '*'
   - Example: `ALLOWED_HOSTS = ['192.168.1.100', 'timemaster.company.local']`

4. **Use a Production Database**
   - Replace SQLite with PostgreSQL or MySQL for production
   - Update DATABASES setting in settings.py

5. **Enable HTTPS**
   - Configure SSL/TLS certificates
   - Set CSRF_COOKIE_SECURE = True
   - Set SESSION_COOKIE_SECURE = True

6. **Configure Email Backend**
   - Set up email for password reset notifications
   - Update EMAIL settings in settings.py

## Network Deployment

### For Private Network Access:

1. **Run on Network Interface**:
```bash
python manage.py runserver 0.0.0.0:8000
```

2. **Access from Other Machines**:
Replace `localhost` with server's IP address:
```
http://192.168.1.100:8000/timesheet/
```


### Export to CSV
Data can be exported from the admin interface or custom management commands can be created.


## Troubleshooting

### Port Already in Use
```bash
# Use different port
python manage.py runserver 0.0.0.0:8001
```

### Static Files Not Loading
```bash
python manage.py collectstatic
```

### Permission Denied
Ensure the user running Django has read/write permissions to the project directory.


## License
Internal Use Only - Company Proprietary

---

**Version**: 1.0.0  
**Last Updated**: April 2026
