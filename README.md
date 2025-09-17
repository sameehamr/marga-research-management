# Marga Research Institute Management System

A comprehensive web-based project management system designed specifically for research institutes to manage research projects, users, and administrative tasks.

## 🚀 Features

### **Core Project Management**
- ✅ **Project CRUD Operations** - Create, view, edit, and delete research projects
- ✅ **Advanced Search & Filtering** - Multi-criteria search with date ranges, status, category, theme, and funding source
- ✅ **Bulk Import/Export** - Excel-based bulk import with data validation and CSV export
- ✅ **Project Status Workflow** - Structured status transitions (Active → On Hold → Completed/Cancelled)
- ✅ **Smart Project ID Generation** - Automatic ID generation using year from start/end dates

### **User Management & Security**
- ✅ **Role-Based Access Control** - Three access levels (Manager, Researcher, Assistant)
- ✅ **User Account Management** - Web-based user administration interface
- ✅ **Password Management** - Self-service password reset and change functionality
- ✅ **Session Management** - 30-minute timeout with warnings and session extension

### **Advanced Features**
- ✅ **Audit Trail** - Comprehensive activity logging for all user actions
- ✅ **Database Backup System** - Automated backup creation, download, and restore
- ✅ **Error Handling & Logging** - Structured error logging with admin management interface
- ✅ **Data Validation** - Comprehensive validation for dates, budgets, and business logic
- ✅ **Responsive Design** - Bootstrap-based UI that works on desktop and mobile

## 🛠️ Technology Stack

- **Backend**: Python 3.11+ with Flask
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Authentication**: Flask-Login with session management
- **File Processing**: Pandas for Excel import/export
- **Security**: Werkzeug password hashing

## 📋 Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- Modern web browser

## 🚀 Installation & Setup

### **1. Clone the Repository**
```bash
git clone https://github.com/yourusername/marga-research-management.git
cd marga-research-management
```

### **2. Create Virtual Environment**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

### **3. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **4. Initialize Database**
```bash
cd research_db
python init_users.py
```

### **5. Run the Application**
```bash
python app.py
```

Open your browser and navigate to `http://127.0.0.1:5000`

## 👥 Default User Accounts

| Username | Password | Access Level | Permissions |
|----------|----------|--------------|-------------|
| manager | manager123 | Full Access | All features including user management |
| researcher | researcher123 | View All | View all projects, limited editing |
| assistant | assistant123 | View Limited | Basic project viewing |

## 📁 Project Structure

```
marga_db/
├── research_db/
│   ├── app.py                 # Main Flask application
│   ├── models.py              # Database models
│   ├── init_users.py          # User initialization script
│   ├── templates/             # HTML templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── projects.html
│   │   ├── add_project.html
│   │   ├── edit_project.html
│   │   ├── bulk_import.html
│   │   └── ...
│   ├── static/               # Static files (CSS, JS, images)
│   └── research_projects.db  # SQLite database
├── requirements.txt          # Python dependencies
├── README.md                # This file
└── .gitignore               # Git ignore rules
```

## 📊 Database Schema

### **Main Tables**
- **users** - User accounts and access levels
- **project** - Research project data
- **audit_log** - Activity and action logging
- **project_status_history** - Project status change tracking
- **error_log** - Application error logging

## 🔧 Key Features Guide

### **Project Management**
1. **Add Projects**: Use the web form or bulk import via Excel
2. **Search & Filter**: Use the comprehensive filter system on the projects page
3. **Status Management**: Track project progress through defined workflow states
4. **Export Data**: Download project data as CSV for external analysis

### **Admin Features**
1. **User Management**: Add, edit, and manage user accounts via web interface
2. **Database Backup**: Create, download, and restore database backups
3. **Audit Logs**: Monitor all user activities and system changes
4. **Error Monitoring**: View and manage application errors

### **Bulk Import**
1. Prepare Excel file with required columns: `title`, `principal_investigator`, `start_date`, `end_date`, `status`
2. Use the "Bulk Import" feature on the projects page
3. Preview data before confirming import
4. System validates data and generates unique project IDs

## 🔒 Security Features

- **Password Hashing**: Secure password storage using Werkzeug
- **Session Management**: Automatic timeout and secure session handling
- **Access Control**: Role-based permissions for different user levels
- **Audit Trail**: Complete logging of all user actions
- **Data Validation**: Comprehensive input validation and sanitization

## 🚀 Deployment

### **Production Considerations**
1. **Database**: Consider migrating to PostgreSQL for production
2. **Web Server**: Use Gunicorn + Nginx for production deployment
3. **Environment Variables**: Use environment variables for sensitive configuration
4. **SSL**: Enable HTTPS for secure communication
5. **Backups**: Implement automated backup scheduling

### **Environment Variables**
Create a `.env` file for production:
```
FLASK_ENV=production
SECRET_KEY=your-secure-secret-key
DATABASE_URL=your-database-url
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support, please create an issue on GitHub or contact the development team.

## 🔄 Version History

- **v1.0.0** - Initial release with core project management features
- **v1.1.0** - Added advanced search, filtering, and bulk import
- **v1.2.0** - Implemented user management and security features
- **v1.3.0** - Added audit trail, error logging, and backup system

---

**Developed for Marga Research Institute** 🏛️