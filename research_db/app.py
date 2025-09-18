from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from werkzeug.security import check_password_hash
from models import db, User, Project, AuditLog, ProjectStatusHistory, ErrorLog
import os
import csv
import io
import json
import logging
import traceback
from datetime import datetime, timedelta
import sys
import pandas as pd

print("Initializing Marga Research Institute Management System...")

# Configure logging
def setup_logging():
    """Configure application logging"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Main application log
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'app.log')),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Error log
    error_logger = logging.getLogger('error_logger')
    error_handler = logging.FileHandler(os.path.join(log_dir, 'errors.log'))
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d')
    error_handler.setFormatter(error_formatter)
    error_logger.addHandler(error_handler)
    
    return logging.getLogger(__name__), error_logger

app_logger, error_logger = setup_logging()

def log_error(error, context=None, user=None):
    """Log application errors with context"""
    try:
        error_details = {
            'error': str(error),
            'type': type(error).__name__,
            'traceback': traceback.format_exc(),
            'context': context or {},
            'user': user.username if user else 'anonymous',
            'timestamp': datetime.now().isoformat(),
            'url': request.url if request else None,
            'method': request.method if request else None,
            'ip': request.remote_addr if request else None
        }
        
        # Log to file
        error_logger.error(json.dumps(error_details, indent=2))
        
        # Also create audit log entry for tracking
        if current_user and current_user.is_authenticated:
            audit_entry = AuditLog(
                user_id=current_user.id,
                action='error_occurred',
                resource_type='system',
                resource_id=None,
                details=json.dumps({
                    'error_type': type(error).__name__,
                    'error_message': str(error),
                    'context': context
                }),
                ip_address=request.remote_addr if request else None,
                user_agent=request.headers.get('User-Agent') if request else None
            )
            db.session.add(audit_entry)
            db.session.commit()
            
    except Exception as e:
        # Fallback logging if even error logging fails
        print(f"Critical: Error logging failed: {e}")

def handle_database_error(func):
    """Decorator for database error handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            db.session.rollback()
            log_error(e, {'function': func.__name__}, current_user if current_user.is_authenticated else None)
            flash('A database error occurred. Please try again or contact support.', 'error')
            return redirect(request.referrer or url_for('dashboard'))
    return wrapper

def log_user_activity(action, resource_type=None, resource_id=None, details=None):
    """Log user activity for audit trail"""
    try:
        if current_user.is_authenticated:
            audit_entry = AuditLog(
                user_id=current_user.id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=json.dumps(details) if details else None,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            db.session.add(audit_entry)
            db.session.commit()
    except Exception as e:
        print(f"Error logging activity: {e}")
        # Don't let audit logging failures break the application

def get_valid_status_transitions():
    """Define valid status transitions"""
    return {
        'Active': ['On Hold', 'Completed', 'Cancelled'],
        'On Hold': ['Active', 'Cancelled'],
        'Completed': [],  # Final state, no transitions allowed
        'Cancelled': []   # Final state, no transitions allowed
    }

def validate_status_transition(current_status, new_status):
    """Validate if a status transition is allowed"""
    if not current_status:  # New project
        return new_status in ['Active']  # New projects start as Active
    
    valid_transitions = get_valid_status_transitions()
    return new_status in valid_transitions.get(current_status, [])

def get_status_suggestions(project):
    """Get suggested status based on project dates"""
    if not project.start_date:
        return None
    
    now = datetime.now().date()
    
    # If project hasn't started yet
    if project.start_date > now:
        return 'Active'  # Default status for new projects
    
    # If project should have ended
    if project.end_date and project.end_date < now:
        if project.status not in ['Completed', 'Cancelled']:
            return 'Completed'
    
    # If project is in active period
    if project.start_date <= now and (not project.end_date or project.end_date >= now):
        if project.status == 'On Hold':
            return 'Active'
    
    return None

def change_project_status(project, new_status, user, reason=None):
    """Change project status with validation and history tracking"""
    old_status = project.status
    
    # Validate transition
    if not validate_status_transition(old_status, new_status):
        raise ValueError(f"Invalid status transition from '{old_status}' to '{new_status}'")
    
    # Update project status
    project.status = new_status
    project.updated_at = datetime.utcnow()
    
    # Create status history record
    status_change = ProjectStatusHistory(
        project_id=project.id,
        user_id=user.id,
        from_status=old_status,
        to_status=new_status,
        reason=reason
    )
    
    db.session.add(status_change)
    
    # Log the status change
    log_user_activity('status_change', 'project', project.project_id, {
        'from_status': old_status,
        'to_status': new_status,
        'reason': reason,
        'title': project.title
    })
    
    return status_change

# Application start time for uptime calculation
def validate_project_data(form_data, is_edit=False, existing_project=None):
    """Comprehensive project data validation"""
    errors = []
    
    # Required field validation
    title = form_data.get('title', '').strip()
    principal_investigator = form_data.get('principal_investigator', '').strip()
    
    if not title:
        errors.append("Project title is required.")
    elif len(title) < 3:
        errors.append("Project title must be at least 3 characters long.")
    elif len(title) > 200:
        errors.append("Project title cannot exceed 200 characters.")
    
    if not principal_investigator:
        errors.append("Principal Investigator is required.")
    elif len(principal_investigator) < 2:
        errors.append("Principal Investigator name must be at least 2 characters long.")
    
    # Date validation
    start_date_str = form_data.get('start_date', '').strip()
    end_date_str = form_data.get('end_date', '').strip()
    
    start_date_obj = None
    end_date_obj = None
    
    if start_date_str:
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            # Check if start date is too far in the past (more than 50 years)
            if start_date_obj.year < datetime.now().year - 50:
                errors.append("Start date cannot be more than 50 years in the past.")
            # Check if start date is too far in the future (more than 10 years)
            elif start_date_obj.year > datetime.now().year + 10:
                errors.append("Start date cannot be more than 10 years in the future.")
        except ValueError:
            errors.append("Invalid start date format. Please use YYYY-MM-DD.")
    
    if end_date_str:
        try:
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            # Check if end date is too far in the future (more than 20 years)
            if end_date_obj.year > datetime.now().year + 20:
                errors.append("End date cannot be more than 20 years in the future.")
        except ValueError:
            errors.append("Invalid end date format. Please use YYYY-MM-DD.")
    
    # Date logic validation
    if start_date_obj and end_date_obj:
        if end_date_obj < start_date_obj:
            errors.append("End date cannot be earlier than start date.")
        
        # Check for unreasonably long projects (more than 15 years)
        project_duration = end_date_obj - start_date_obj
        if project_duration.days > 15 * 365:
            errors.append("Project duration cannot exceed 15 years.")
    
    # Budget validation
    budget_str = form_data.get('budget', '').strip()
    if budget_str:
        try:
            budget_val = float(budget_str)
            if budget_val < 0:
                errors.append("Budget cannot be negative.")
            elif budget_val > 10000000000:  # 10 billion limit
                errors.append("Budget cannot exceed 10 billion.")
        except ValueError:
            errors.append("Budget must be a valid number.")
    
    # Currency validation
    currency = form_data.get('currency', '').strip()
    valid_currencies = ['Rs', 'USD', 'EUR', 'GBP', 'INR', 'AUD', 'CAD', 'JPY', 'CNY', 'SGD', 'HKD', 'THB', 'MYR', 'PKR', 'BDT', 'NPR']
    if currency and currency not in valid_currencies:
        errors.append(f"Invalid currency. Must be one of: {', '.join(valid_currencies)}")
    
    # Status validation
    status = form_data.get('status', '').strip()
    valid_statuses = ['Active', 'On Hold', 'Completed', 'Cancelled']
    if status and status not in valid_statuses:
        errors.append(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    # Description validation
    description = form_data.get('description', '').strip()
    if description and len(description) > 5000:
        errors.append("Description cannot exceed 5000 characters.")
    
    # Team members validation
    team_members = form_data.get('team_members', '').strip()
    if team_members and len(team_members) > 1000:
        errors.append("Team members field cannot exceed 1000 characters.")
    
    # Funding source validation
    funding_source = form_data.get('funding_source', '').strip()
    if funding_source and len(funding_source) > 200:
        errors.append("Funding source cannot exceed 200 characters.")
    
    # Category and theme validation
    category = form_data.get('category', '').strip()
    if category and len(category) > 100:
        errors.append("Category cannot exceed 100 characters.")
    
    theme = form_data.get('theme', '').strip()
    if theme and len(theme) > 100:
        errors.append("Theme cannot exceed 100 characters.")
    
    # Duplicate title check (only for new projects or if title changed)
    if not is_edit or (existing_project and existing_project.title != title):
        existing_title = Project.query.filter_by(title=title).first()
        if existing_title:
            errors.append("A project with this title already exists. Please choose a different title.")
    
    return errors, {
        'title': title,
        'principal_investigator': principal_investigator,
        'start_date_obj': start_date_obj,
        'end_date_obj': end_date_obj,
        'budget_val': float(budget_str) if budget_str else None,
        'description': description,
        'category': category,
        'theme': theme,
        'status': status,
        'team_members': team_members,
        'funding_source': funding_source,
        'currency': currency
    }

def validate_bulk_import_data(df):
    """Validate bulk import data for common issues"""
    issues = []
    
    # Check for required columns using the same mapping as process_import_data
    required_fields = {
        'title': ['title', 'project title', 'name', 'project name'],
        'principal_investigator': ['principal investigator', 'pi', 'lead', 'principal_investigator']
    }
    
    df_columns_lower = [col.lower().strip() for col in df.columns]
    
    for field_name, possible_names in required_fields.items():
        found = False
        for name in possible_names:
            if name.lower() in df_columns_lower:
                found = True
                break
        if not found:
            display_name = 'Principal Investigator' if field_name == 'principal_investigator' else field_name.title()
            issues.append(f"Missing required column: '{display_name}' (or similar: {', '.join(possible_names)})")
    
    # Check for empty rows
    if df.empty:
        issues.append("The file contains no data rows.")
    
    # Check for duplicate titles with similar dates
    if 'title' in df.columns:
        # Get columns for dates
        date_cols = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower in ['start date', 'start_date', 'begin date', 'commencement']:
                date_cols['start'] = col
            elif col_lower in ['end date', 'end_date', 'finish date', 'completion']:
                date_cols['end'] = col
        
        # Check for duplicates based on title and dates
        duplicate_groups = []
        df_copy = df.copy()
        df_copy['title_clean'] = df_copy['title'].str.strip().str.lower()
        
        # Group by title
        title_groups = df_copy.groupby('title_clean')
        
        for title, group in title_groups:
            if len(group) > 1:
                # Check if dates are similar for duplicates
                similar_found = False
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        row1 = group.iloc[i]
                        row2 = group.iloc[j]
                        
                        # Compare dates if available
                        dates_similar = True
                        if date_cols.get('start') and pd.notna(row1[date_cols['start']]) and pd.notna(row2[date_cols['start']]):
                            try:
                                date1 = pd.to_datetime(row1[date_cols['start']])
                                date2 = pd.to_datetime(row2[date_cols['start']])
                                # Consider dates similar if within 30 days
                                if abs((date1 - date2).days) > 30:
                                    dates_similar = False
                            except:
                                pass
                        
                        if date_cols.get('end') and pd.notna(row1[date_cols['end']]) and pd.notna(row2[date_cols['end']]):
                            try:
                                date1 = pd.to_datetime(row1[date_cols['end']])
                                date2 = pd.to_datetime(row2[date_cols['end']])
                                # Consider dates similar if within 30 days
                                if abs((date1 - date2).days) > 30:
                                    dates_similar = False
                            except:
                                pass
                        
                        if dates_similar:
                            duplicate_groups.append(row1['title'])
                            similar_found = True
                            break
                    if similar_found:
                        break
        
        if duplicate_groups:
            unique_duplicates = list(set(duplicate_groups))
            issues.append(f"Duplicate projects found (same title and similar dates): {', '.join(unique_duplicates[:5])}")
            if len(unique_duplicates) > 5:
                issues.append(f"... and {len(unique_duplicates) - 5} more duplicates")
    
    # Check for invalid dates
    date_columns = ['start date', 'start_date', 'end date', 'end_date']
    for col in df.columns:
        if col.lower().strip() in date_columns:
            try:
                pd.to_datetime(df[col], errors='coerce')
            except Exception:
                issues.append(f"Invalid date format in column '{col}'")
    
    # Check for invalid budget values
    budget_columns = ['budget', 'amount', 'funding amount']
    for col in df.columns:
        if col.lower().strip() in budget_columns:
            try:
                pd.to_numeric(df[col], errors='coerce')
            except Exception:
                issues.append(f"Invalid numeric values in budget column '{col}'")
    
    return issues

def create_app():
    """Application factory pattern"""
    
    app = Flask(__name__)
    
    # Configure the app directly
    app.config['SECRET_KEY'] = 'marga-research-secret-key-2024'
    
    # Use absolute path for database to ensure consistency
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'research_projects.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Session timeout configuration (30 minutes)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SESSION_TIMEOUT_WARNING'] = 5  # Warn 5 minutes before timeout
    
    # Initialize extensions
    db.init_app(app)
    
    # Setup login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        app_logger.warning(f"404 error: {request.url}")
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        log_error(error, {'error_type': '500_internal_server_error'})
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        app_logger.warning(f"403 error: {request.url} - User: {current_user.username if current_user.is_authenticated else 'Anonymous'}")
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all unhandled exceptions"""
        db.session.rollback()
        log_error(error, {'error_type': 'unhandled_exception'})
        
        # Return 500 for unhandled exceptions
        return render_template('errors/500.html'), 500
    
    return app

# Create application instance
app = create_app()

@app.before_request
def check_session_timeout():
    """Check if session has timed out"""
    # Skip timeout check for login/logout pages and static files
    exempt_endpoints = ['login', 'logout', 'static', 'health_check']
    
    if request.endpoint in exempt_endpoints or request.endpoint is None:
        return
    
    # Check if user is authenticated
    if current_user.is_authenticated:
        # Check if session has last_activity timestamp
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            timeout_duration = app.config['PERMANENT_SESSION_LIFETIME']
            
            if datetime.now() - last_activity > timeout_duration:
                # Session has expired
                logout_user()
                session.clear()
                
                # Log session timeout
                try:
                    timeout_log = AuditLog(
                        user_id=None,
                        action='session_timeout',
                        resource_type='system',
                        resource_id=None,
                        details=json.dumps({'timeout_duration_minutes': timeout_duration.total_seconds()/60}),
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent')
                    )
                    db.session.add(timeout_log)
                    db.session.commit()
                except:
                    pass
                
                flash('Your session has expired due to inactivity. Please log in again.', 'warning')
                return redirect(url_for('login'))
        
        # Update last activity timestamp
        session['last_activity'] = datetime.now().isoformat()
        session.permanent = True

@app.context_processor
def inject_session_info():
    """Inject session timeout information into templates"""
    if current_user.is_authenticated and 'last_activity' in session:
        last_activity = datetime.fromisoformat(session['last_activity'])
        timeout_duration = app.config['PERMANENT_SESSION_LIFETIME']
        warning_time = app.config['SESSION_TIMEOUT_WARNING']
        
        time_left = timeout_duration - (datetime.now() - last_activity)
        warning_threshold = timedelta(minutes=warning_time)
        
        return {
            'session_timeout_minutes': int(timeout_duration.total_seconds() / 60),
            'session_warning_minutes': warning_time,
            'session_time_left_seconds': int(time_left.total_seconds()),
            'session_show_warning': time_left <= warning_threshold
        }
    return {}

def generate_project_id(start_date=None, end_date=None):
    """Generate a unique project ID in format PROJ-YYYY-XXX using start date first, then end date, then current date"""
    if start_date:
        project_year = start_date.year
    elif end_date:
        project_year = end_date.year
    else:
        # Fallback to current year if no dates provided
        project_year = datetime.now().year
    
    # Find the highest project number for this year
    existing_projects = Project.query.filter(
        Project.project_id.like(f'PROJ-{project_year}-%')
    ).all()
    
    if not existing_projects:
        # First project of the year
        project_number = 1
    else:
        # Extract numbers from existing project IDs and find the highest
        numbers = []
        for project in existing_projects:
            try:
                # Extract number from "PROJ-YYYY-XXX" format
                parts = project.project_id.split('-')
                if len(parts) == 3 and parts[0] == 'PROJ' and parts[1] == str(project_year):
                    numbers.append(int(parts[2]))
            except (ValueError, IndexError):
                continue
        
        project_number = max(numbers) + 1 if numbers else 1
    
    # Format as PROJ-YYYY-XXX (with leading zeros)
    return f"PROJ-{project_year}-{project_number:03d}"

# Create tables when app starts
with app.app_context():
    db.create_all()
    
    # Clean up old temporary import files on startup
    try:
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
        if os.path.exists(temp_dir):
            import glob
            import time
            
            # Remove files older than 1 hour
            current_time = time.time()
            temp_files = glob.glob(os.path.join(temp_dir, 'import_*.pkl'))
            
            for temp_file in temp_files:
                if current_time - os.path.getmtime(temp_file) > 3600:  # 1 hour
                    try:
                        os.remove(temp_file)
                        print(f"Cleaned up old temp file: {temp_file}")
                    except:
                        pass
    except Exception as e:
        print(f"Warning: Could not clean up temp files: {e}")

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get project statistics
    total_projects = Project.query.count()
    active_projects = Project.query.filter_by(status='Active').count()
    completed_projects = Project.query.filter_by(status='Completed').count()
    on_hold_projects = Project.query.filter_by(status='On Hold').count()
    
    # Get budget analysis for users who can view budgets
    budget_analysis = {}
    if current_user.can_view_budget():
        # Calculate total budget by currency
        projects_with_budget = Project.query.filter(Project.budget.isnot(None)).all()
        
        currency_totals = {}
        for project in projects_with_budget:
            currency = project.currency or 'Unknown'
            budget = project.budget or 0
            if currency in currency_totals:
                currency_totals[currency] += budget
            else:
                currency_totals[currency] = budget
        
        budget_analysis = {
            'currency_totals': currency_totals,
            'projects_with_budget': len(projects_with_budget),
            'projects_without_budget': total_projects - len(projects_with_budget)
        }
    
    # Get recent projects (last 5)
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(5).all()
    
    # Get active projects for display
    current_active_projects = Project.query.filter_by(status='Active').order_by(Project.start_date.desc()).limit(10).all()
    
    # Get all projects for display (last 10)
    all_recent_projects = Project.query.order_by(Project.created_at.desc()).limit(10).all()
    
    # Get next project ID for admin users (using current year as example)
    next_project_id = generate_project_id() if current_user.can_edit_projects() else None
    
    stats = {
        'total': total_projects,
        'active': active_projects,
        'completed': completed_projects,
        'on_hold': on_hold_projects,
        'recent_projects': recent_projects,
        'next_project_id': next_project_id,
        'current_active_projects': current_active_projects,
        'all_recent_projects': all_recent_projects,
        'budget_analysis': budget_analysis
    }
    
    return render_template('dashboard.html', stats=stats)

@app.route('/all-projects')
@login_required
def all_projects():
    all_projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('projects.html', projects=all_projects)

@app.route('/projects')
@login_required
def projects():
    # Get search and filter parameters
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    funding_source_filter = request.args.get('funding_source', '').strip()
    category_filter = request.args.get('category', '').strip()
    theme_filter = request.args.get('theme', '').strip()
    currency_filter = request.args.get('currency', '').strip()
    start_date_filter = request.args.get('start_date', '')
    end_date_filter = request.args.get('end_date', '')
    
    # Get sorting parameters
    sort_by = request.args.get('sort', 'created_at')  # Default sort by created_at
    sort_order = request.args.get('order', 'desc')   # Default descending order (newest first)
    
    # Start with base query
    query = Project.query
    
    # Apply search filter (search in title, description, PI, team members, project_id)
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            db.or_(
                Project.title.ilike(search_pattern),
                Project.description.ilike(search_pattern),
                Project.principal_investigator.ilike(search_pattern),
                Project.team_members.ilike(search_pattern),
                Project.project_id.ilike(search_pattern),
                Project.category.ilike(search_pattern),
                Project.theme.ilike(search_pattern)
            )
        )
    
    # Apply status filter
    if status_filter:
        query = query.filter(Project.status == status_filter)
    
    # Apply funding source filter
    if funding_source_filter:
        funding_pattern = f'%{funding_source_filter}%'
        query = query.filter(Project.funding_source.ilike(funding_pattern))
    
    # Apply category filter
    if category_filter:
        category_pattern = f'%{category_filter}%'
        query = query.filter(Project.category.ilike(category_pattern))
    
    # Apply theme filter
    if theme_filter:
        theme_pattern = f'%{theme_filter}%'
        query = query.filter(Project.theme.ilike(theme_pattern))
    
    # Apply currency filter
    if currency_filter:
        query = query.filter(Project.currency == currency_filter)
    
    # Apply date range filters
    if start_date_filter:
        from datetime import datetime
        start_date_obj = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
        query = query.filter(Project.start_date >= start_date_obj)
    
    if end_date_filter:
        from datetime import datetime
        end_date_obj = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
        query = query.filter(Project.start_date <= end_date_obj)
    

    
    # Apply sorting
    valid_sort_columns = {
        'project_id': Project.project_id,
        'title': Project.title,
        'principal_investigator': Project.principal_investigator,
        'start_date': Project.start_date,
        'end_date': Project.end_date,
        'status': Project.status,
        'budget': Project.budget,
        'category': Project.category,
        'theme': Project.theme,
        'created_at': Project.created_at
    }
    
    if sort_by in valid_sort_columns:
        sort_column = valid_sort_columns[sort_by]
        if sort_order == 'asc':
            # Handle null values for date sorting - put nulls last
            if sort_by in ['start_date', 'end_date', 'budget']:
                query = query.order_by(sort_column.asc().nullslast())
            else:
                query = query.order_by(sort_column.asc())
        else:
            # Handle null values for date sorting - put nulls last
            if sort_by in ['start_date', 'end_date', 'budget']:
                query = query.order_by(sort_column.desc().nullslast())
            else:
                query = query.order_by(sort_column.desc())
    else:
        # Default sort
        query = query.order_by(Project.created_at.desc())
    
    # Get filtered results
    projects = query.all()
    
    # Define available statuses for filter dropdown
    statuses = ['Active', 'On Hold', 'Completed', 'Cancelled']
    
    # Get unique values for filter dropdowns
    all_funding_sources = db.session.query(Project.funding_source.distinct()).all()
    funding_sources = [source[0] for source in all_funding_sources if source[0] and source[0].strip()]
    
    all_categories = db.session.query(Project.category.distinct()).all()
    categories = [cat[0] for cat in all_categories if cat[0] and cat[0].strip()]
    
    all_themes = db.session.query(Project.theme.distinct()).all()
    themes = [theme[0] for theme in all_themes if theme[0] and theme[0].strip()]
    
    all_currencies = db.session.query(Project.currency.distinct()).all()
    currencies = [curr[0] for curr in all_currencies if curr[0] and curr[0].strip()]
    
    return render_template('projects.html', 
                         projects=projects, 
                         statuses=statuses,
                         funding_sources=funding_sources,
                         categories=categories,
                         themes=themes,
                         currencies=currencies,
                         search_query=search_query,
                         status_filter=status_filter,
                         funding_source_filter=funding_source_filter,
                         category_filter=category_filter,
                         theme_filter=theme_filter,
                         currency_filter=currency_filter,
                         start_date_filter=start_date_filter,
                         end_date_filter=end_date_filter,
                         sort_by=sort_by,
                         sort_order=sort_order)

@app.route('/projects/export/csv')
@login_required
def export_projects_csv():
    """Export projects to CSV file"""
    from datetime import datetime
    
    # Get the same filtered projects as the main projects page
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    funding_source_filter = request.args.get('funding_source', '').strip()
    start_date_filter = request.args.get('start_date', '')
    end_date_filter = request.args.get('end_date', '')
    
    # Start with base query
    query = Project.query
    
    # Apply search filter
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            db.or_(
                Project.title.ilike(search_pattern),
                Project.description.ilike(search_pattern),
                Project.principal_investigator.ilike(search_pattern),
                Project.team_members.ilike(search_pattern)
            )
        )
    
    # Apply status filter
    if status_filter:
        query = query.filter(Project.status == status_filter)
    
    # Apply funding source filter
    if funding_source_filter:
        funding_pattern = f'%{funding_source_filter}%'
        query = query.filter(Project.funding_source.ilike(funding_pattern))
    
    # Apply date range filters
    if start_date_filter:
        start_date_obj = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
        query = query.filter(Project.start_date >= start_date_obj)
    
    if end_date_filter:
        end_date_obj = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
        query = query.filter(Project.start_date <= end_date_obj)
    
    # Get sorting parameters (same as main projects view)
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    # Apply sorting
    valid_sort_columns = {
        'project_id': Project.project_id,
        'title': Project.title,
        'principal_investigator': Project.principal_investigator,
        'start_date': Project.start_date,
        'end_date': Project.end_date,
        'status': Project.status,
        'created_at': Project.created_at
    }
    
    if sort_by in valid_sort_columns:
        sort_column = valid_sort_columns[sort_by]
        if sort_order == 'asc':
            if sort_by in ['start_date', 'end_date']:
                query = query.order_by(sort_column.asc().nullslast())
            else:
                query = query.order_by(sort_column.asc())
        else:
            if sort_by in ['start_date', 'end_date']:
                query = query.order_by(sort_column.desc().nullslast())
            else:
                query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(Project.created_at.desc())
    
    # Get filtered results
    projects = query.all()
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Determine CSV header based on user permissions
    if current_user.can_view_budget():
        header = [
            'Project ID', 'Title', 'Description', 'Category', 'Theme',
            'Principal Investigator', 'Team Members', 'Start Date', 'End Date',
            'Status', 'Budget', 'Currency', 'Funding Source', 'Created At'
        ]
    else:
        header = [
            'Project ID', 'Title', 'Description', 'Category', 'Theme',
            'Principal Investigator', 'Team Members', 'Start Date', 'End Date',
            'Status', 'Funding Source', 'Created At'
        ]
    
    writer.writerow(header)
    
    # Write project data
    for project in projects:
        if current_user.can_view_budget():
            row = [
                project.project_id or '',
                project.title or '',
                project.description or '',
                project.category or '',
                project.theme or '',
                project.principal_investigator or '',
                project.team_members or '',
                project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
                project.end_date.strftime('%Y-%m-%d') if project.end_date else '',
                project.status or '',
                f'{project.budget:.2f}' if project.budget else '',
                project.currency or 'Rs',
                project.funding_source or '',
                project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else ''
            ]
        else:
            row = [
                project.project_id or '',
                project.title or '',
                project.description or '',
                project.category or '',
                project.theme or '',
                project.principal_investigator or '',
                project.team_members or '',
                project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
                project.end_date.strftime('%Y-%m-%d') if project.end_date else '',
                project.status or '',
                project.funding_source or '',
                project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else ''
            ]
        writer.writerow(row)
    
    # Create response
    output.seek(0)
    filename = f'marga_research_projects_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            # Make session permanent to ensure it's saved
            session.permanent = True
            session['last_activity'] = datetime.now().isoformat()
            login_user(user, remember=True)
            
            # Log successful login
            log_user_activity('login', 'system', None, {
                'username': username,
                'login_method': 'password'
            })
            
            flash(f'Welcome back, {user.full_name}!', 'success')
            
            # Check if user needs to change password
            if hasattr(user, 'force_password_change') and user.force_password_change:
                flash('You must change your password before continuing.', 'warning')
                return redirect(url_for('change_password'))
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            redirect_url = url_for('home') if not next_page else next_page
            return redirect(redirect_url)
        else:
            # Log failed login attempt
            try:
                # Create a temporary audit entry for failed login (without user_id)
                failed_login = AuditLog(
                    user_id=None,  # No user for failed login
                    action='login_failed',
                    resource_type='system',
                    resource_id=None,
                    details=json.dumps({'username': username, 'reason': 'invalid_credentials'}),
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                db.session.add(failed_login)
                db.session.commit()
            except:
                pass  # Don't break login on audit failure
                
            flash('Invalid username or password. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset request page"""
    if request.method == 'POST':
        username = request.form['username'].strip()
        user = User.query.filter_by(username=username).first()
        
        if user:
            # Generate temporary password
            import secrets
            import string
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
            
            # Store temporary password
            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash(temp_password)
            
            # Set a flag to force password change on next login
            # (We'll add this field to the User model)
            db.session.commit()
            
            flash(f'Password reset for "{username}". Your temporary password is: {temp_password}', 'success')
            flash('Please use this temporary password to log in and change your password immediately.', 'warning')
            return redirect(url_for('login'))
        else:
            # For security, don't reveal if username exists or not
            flash('If the username exists, a temporary password has been generated. Contact admin if needed.', 'info')
    
    return render_template('forgot_password.html')

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Allow users to change their own password"""
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Check if current password is correct
        if not check_password_hash(current_user.password_hash, current_password):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('change_password'))
        
        # Validate new password
        if len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'error')
            return redirect(url_for('change_password'))
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('change_password'))
        
        try:
            # Update password
            from werkzeug.security import generate_password_hash
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            flash('Password changed successfully.', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error changing password: {str(e)}', 'error')
    
    return render_template('change_password.html')

@app.route('/logout')
@login_required
def logout():
    # Log logout before actually logging out
    if current_user.is_authenticated:
        log_user_activity('logout', 'system', None, {'logout_method': 'manual'})
    
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/projects/add', methods=['GET', 'POST'])
@login_required
def add_project():
    # Only users with full access can add projects
    if not current_user.can_edit_projects():
        flash('You do not have permission to add projects.', 'error')
        return redirect(url_for('projects'))
    
    if request.method == 'POST':
        try:
            # Validate form data
            validation_errors, validated_data = validate_project_data(request.form)
            
            if validation_errors:
                for error in validation_errors:
                    flash(error, 'error')
                return render_template('add_project.html')
            
            # Auto-generate project ID using start date first, then end date, then current year
            project_id = generate_project_id(validated_data['start_date_obj'], validated_data['end_date_obj'])
            
            # Create project with validated data
            project = Project(
                project_id=project_id,
                title=validated_data['title'],
                description=validated_data['description'],
                category=validated_data['category'],
                theme=validated_data['theme'],
                start_date=validated_data['start_date_obj'],
                end_date=validated_data['end_date_obj'],
                status=validated_data['status'],
                principal_investigator=validated_data['principal_investigator'],
                team_members=validated_data['team_members'],
                budget=validated_data['budget_val'],
                currency=validated_data['currency'],
                funding_source=validated_data['funding_source'],
                created_at=datetime.utcnow(),  # Use UTC time for consistency
                updated_at=datetime.utcnow()   # Use UTC time for consistency
            )
            
            db.session.add(project)
            db.session.commit()
            
            # Log project creation
            log_user_activity('create_project', 'project', project_id, {
                'title': validated_data['title'],
                'status': validated_data['status'],
                'budget': float(validated_data['budget_val']) if validated_data['budget_val'] else None,
                'currency': validated_data['currency']
            })
            
            flash(f'Project "{validated_data["title"]}" has been added successfully with ID: {project_id}!', 'success')
            return redirect(url_for('projects'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while adding the project: {str(e)}', 'error')
            return render_template('add_project.html')
    
    return render_template('add_project.html')

@app.route('/projects/<int:id>')
@login_required
def view_project(id):
    project = Project.query.get_or_404(id)
    return render_template('view_project.html', project=project)

@app.route('/projects/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(id):
    # Only users with full access can edit projects
    if not current_user.can_edit_projects():
        flash('You do not have permission to edit projects.', 'error')
        return redirect(url_for('projects'))
    
    project = Project.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Validate form data
            validation_errors, validated_data = validate_project_data(request.form, is_edit=True, existing_project=project)
            
            if validation_errors:
                for error in validation_errors:
                    flash(error, 'error')
                return render_template('edit_project.html', project=project)
            
            # Store original values for audit log
            original_values = {
                'title': project.title,
                'status': project.status,
                'budget': float(project.budget) if project.budget else None,
                'currency': project.currency
            }
            
            # Check if status is changing and validate transition
            status_changed = False
            if original_values['status'] != validated_data['status']:
                status_changed = True
                if not validate_status_transition(original_values['status'], validated_data['status']):
                    flash(f"Invalid status transition from '{original_values['status']}' to '{validated_data['status']}'", 'error')
                    return render_template('edit_project.html', project=project)
            
            # Update project with validated data (except status - handled separately)
            project.title = validated_data['title']
            project.description = validated_data['description']
            project.category = validated_data['category']
            project.theme = validated_data['theme']
            project.start_date = validated_data['start_date_obj']
            project.end_date = validated_data['end_date_obj']
            project.principal_investigator = validated_data['principal_investigator']
            project.team_members = validated_data['team_members']
            project.budget = validated_data['budget_val']
            project.currency = validated_data['currency']
            project.funding_source = validated_data['funding_source']
            
            # Handle status change through workflow if status changed
            if status_changed:
                change_project_status(project, validated_data['status'], current_user, 
                                    f"Status changed during project edit")
            
            db.session.commit()
            
            # Log project edit with changes
            changes = {}
            if original_values['title'] != validated_data['title']:
                changes['title'] = {'from': original_values['title'], 'to': validated_data['title']}
            if original_values['status'] != validated_data['status']:
                changes['status'] = {'from': original_values['status'], 'to': validated_data['status']}
            if original_values['budget'] != (float(validated_data['budget_val']) if validated_data['budget_val'] else None):
                changes['budget'] = {'from': original_values['budget'], 'to': float(validated_data['budget_val']) if validated_data['budget_val'] else None}
            
            log_user_activity('edit_project', 'project', project.project_id, {
                'title': validated_data['title'],
                'changes': changes
            })
            
            flash(f'Project "{validated_data["title"]}" has been updated successfully!', 'success')
            return redirect(url_for('view_project', id=project.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating the project: {str(e)}', 'error')
            return render_template('edit_project.html', project=project)
    
    return render_template('edit_project.html', project=project)

@app.route('/projects/<int:id>/delete', methods=['POST'])
@login_required
def delete_project(id):
    # Only users with full access can delete projects
    if not current_user.can_edit_projects():
        flash('You do not have permission to delete projects.', 'error')
        return redirect(url_for('projects'))
    
    project = Project.query.get_or_404(id)
    project_title = project.title
    project_id = project.project_id
    
    try:
        # Log project deletion before actually deleting
        log_user_activity('delete_project', 'project', project_id, {
            'title': project_title,
            'status': project.status,
            'budget': float(project.budget) if project.budget else None
        })
        
        db.session.delete(project)
        db.session.commit()
        flash(f'Project "{project_title}" has been deleted successfully.', 'success')
    except Exception as e:
        flash('An error occurred while deleting the project. Please try again.', 'error')
    
    return redirect(url_for('projects'))

@app.route('/projects/<int:id>/refresh-timestamp', methods=['POST'])
@login_required
def refresh_project_timestamp(id):
    """Debug route to refresh a project's timestamp"""
    if not current_user.can_edit_projects():
        flash('You do not have permission to edit projects.', 'error')
        return redirect(url_for('projects'))
    
    project = Project.query.get_or_404(id)
    old_timestamp = project.created_at
    
    # Update to current time
    project.created_at = datetime.utcnow()
    project.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash(f'Project timestamp updated from {old_timestamp} to {project.created_at}', 'success')
    return redirect(url_for('projects'))

@app.route('/projects/<int:id>/change-status', methods=['POST'])
@login_required
def change_status(id):
    """Change project status with workflow validation"""
    if not current_user.can_edit_projects():
        flash('You do not have permission to change project status.', 'error')
        return redirect(url_for('projects'))
    
    project = Project.query.get_or_404(id)
    new_status = request.form.get('status', '').strip()
    reason = request.form.get('reason', '').strip()
    
    if not new_status:
        flash('Status is required.', 'error')
        return redirect(url_for('view_project', id=id))
    
    try:
        # Use the status workflow function
        change_project_status(project, new_status, current_user, reason)
        db.session.commit()
        
        flash(f'Project status changed to "{new_status}" successfully.', 'success')
    
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error changing status: {str(e)}', 'error')
    
    return redirect(url_for('view_project', id=id))

@app.route('/projects/<int:id>/status-history')
@login_required
def project_status_history(id):
    """View project status change history"""
    project = Project.query.get_or_404(id)
    
    # Check permissions
    if not current_user.can_view_projects():
        flash('Access denied.', 'error')
        return redirect(url_for('projects'))
    
    return render_template('project_status_history.html', project=project)

# Bulk Import Routes
@app.route('/bulk-import', methods=['GET', 'POST'])
@login_required
def bulk_import():
    """Bulk import projects from Excel/CSV files"""
    if not current_user.can_edit_projects():
        flash('Access denied. Full access privileges required.', 'error')
        return redirect(url_for('projects'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                preview_mode = 'preview_mode' in request.form
                skip_duplicates = 'skip_duplicates' in request.form
                
                # Process the uploaded file
                import pandas as pd
                
                # Read the file based on extension
                if file.filename.lower().endswith('.csv'):
                    df = pd.read_csv(file)
                else:
                    df = pd.read_excel(file)
                
                # Validate bulk import data first
                validation_issues = validate_bulk_import_data(df)
                if validation_issues:
                    for issue in validation_issues:
                        flash(issue, 'error')
                    return render_template('bulk_import.html')
                
                # Process and validate data
                processed_projects = process_import_data(df, skip_duplicates)
                print(f"DEBUG: Processed {len(processed_projects)} projects from import file")
                
                if preview_mode:
                    # Instead of storing full data in session, store a temporary file
                    import tempfile
                    import pickle
                    import uuid
                    
                    # Generate unique identifier for this import
                    import_id = str(uuid.uuid4())
                    
                    # Create temporary file to store import data
                    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
                    if not os.path.exists(temp_dir):
                        os.makedirs(temp_dir)
                    
                    temp_file = os.path.join(temp_dir, f'import_{import_id}.pkl')
                    
                    # Serialize projects to temporary file
                    serialized_data = [serialize_project_for_session(proj) for proj in processed_projects]
                    with open(temp_file, 'wb') as f:
                        pickle.dump(serialized_data, f)
                    
                    # Store only the import ID in session (much smaller)
                    session['import_id'] = import_id
                    session.permanent = True
                    
                    print(f"DEBUG: Stored import data in temp file: {temp_file}")
                    print(f"DEBUG: Session now contains import_id: {import_id}")
                    
                    return render_template('bulk_import.html', preview_data=processed_projects)
                else:
                    # Direct import
                    results = import_projects_to_db(processed_projects)
                    return render_template('bulk_import.html', import_results=results)
                    
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Invalid file format. Please upload Excel (.xlsx, .xls) or CSV (.csv) files only.', 'error')
            return redirect(request.url)
    
    return render_template('bulk_import.html')

@app.route('/confirm-import', methods=['POST'])
@login_required
def confirm_import():
    """Confirm and execute the import after preview"""
    if not current_user.can_edit_projects():
        flash('Access denied. Full access privileges required.', 'error')
        return redirect(url_for('projects'))
    
    # Debug: Check session contents
    print(f"DEBUG: Session keys: {list(session.keys())}")
    print(f"DEBUG: 'import_id' in session: {'import_id' in session}")
    
    if 'import_id' not in session:
        flash('No import data found. Please upload a file first.', 'error')
        print("DEBUG: No import_id in session - redirecting to bulk_import")
        return redirect(url_for('bulk_import'))
    
    try:
        # Get import ID from session
        import_id = session.pop('import_id')
        print(f"DEBUG: Retrieved import_id from session: {import_id}")
        
        # Load data from temporary file
        import pickle
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
        temp_file = os.path.join(temp_dir, f'import_{import_id}.pkl')
        
        if not os.path.exists(temp_file):
            flash('Import data not found. Please upload the file again.', 'error')
            print(f"DEBUG: Temp file not found: {temp_file}")
            return redirect(url_for('bulk_import'))
        
        # Load serialized data
        with open(temp_file, 'rb') as f:
            import_data = pickle.load(f)
        
        print(f"DEBUG: Loaded {len(import_data)} projects from temp file")
        
        # Clean up temporary file
        try:
            os.remove(temp_file)
            print(f"DEBUG: Cleaned up temp file: {temp_file}")
        except:
            pass  # Don't fail if cleanup fails
        
        # Reconstruct project objects from loaded data
        processed_projects = [deserialize_project_from_session(proj_data) for proj_data in import_data]
        print(f"DEBUG: Deserialized {len(processed_projects)} projects")
        
        # Import to database
        results = import_projects_to_db(processed_projects)
        print(f"DEBUG: Import results: {results}")
        return render_template('bulk_import.html', import_results=results)
        
    except Exception as e:
        print(f"DEBUG: Exception in confirm_import: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error during import: {str(e)}', 'error')
        return redirect(url_for('bulk_import'))

@app.route('/download-template')
@login_required
def download_template():
    """Download Excel template for bulk import"""
    if not current_user.can_edit_projects():
        flash('Access denied. Full access privileges required.', 'error')
        return redirect(url_for('projects'))
    
    # Create template data
    template_data = {
        'Title': ['Sample Research Project 1', 'Sample Research Project 2'],
        'Principal Investigator': ['Dr. John Smith', 'Dr. Jane Doe'],
        'Description': ['This is a sample project description', 'Another sample project'],
        'Category': ['Medical Research', 'Environmental Science'],
        'Theme': ['Cancer Research', 'Climate Change'],
        'Status': ['Active', 'Completed'],
        'Start Date': ['2024-01-01', '2023-06-15'],
        'End Date': ['2024-12-31', '2024-06-14'],
        'Team Members': ['Alice Johnson, Bob Wilson', 'Carol Davis'],
        'Funding Source': ['National Science Foundation', 'University Grant'],
        'Budget': ['Rs 5000000', 'USD 25000'],
        'Currency': ['Rs', 'USD']
    }
    
    import pandas as pd
    df = pd.DataFrame(template_data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Projects', index=False)
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=project_import_template.xlsx'}
    )

def serialize_project_for_session(project):
    """Convert project object to JSON-serializable dict for session storage"""
    return {
        'title': project.title,
        'principal_investigator': project.principal_investigator,
        'description': project.description,
        'category': project.category,
        'theme': project.theme,
        'status': project.status,
        'start_date': project.start_date.isoformat() if project.start_date else None,
        'end_date': project.end_date.isoformat() if project.end_date else None,
        'team_members': project.team_members,
        'funding_source': project.funding_source,
        'budget': project.budget,
        'currency': project.currency,
        'project_id': project.project_id
    }

def deserialize_project_from_session(data):
    """Convert session dict back to project object"""
    from datetime import datetime
    
    project = Project()
    project.title = data['title']
    project.principal_investigator = data['principal_investigator']
    project.description = data['description']
    project.category = data['category']
    project.theme = data['theme']
    project.status = data['status']
    project.start_date = datetime.fromisoformat(data['start_date']).date() if data['start_date'] else None
    project.end_date = datetime.fromisoformat(data['end_date']).date() if data['end_date'] else None
    project.team_members = data['team_members']
    project.funding_source = data['funding_source']
    project.budget = data['budget']
    project.currency = data['currency']
    project.project_id = data['project_id']
    project.created_at = datetime.utcnow()  # Use UTC for consistency
    
    return project

def allowed_file(filename):
    """Check if file extension is allowed"""
    allowed_extensions = {'xlsx', 'xls', 'csv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def detect_currency_from_budget(budget_text, currency_text=''):
    """Detect currency from budget text or currency column"""
    import pandas as pd
    
    if pd.isna(budget_text) and pd.isna(currency_text):
        return 'Rs'  # Default to Rs (Sri Lankan Rupees)
    
    # Convert to string for processing
    budget_str = str(budget_text).strip() if not pd.isna(budget_text) else ''
    currency_str = str(currency_text).strip() if not pd.isna(currency_text) else ''
    
    # If currency column has a value, use it
    if currency_str and currency_str.lower() not in ['nan', 'none', '']:
        return currency_str
    
    # Try to detect currency from budget text
    budget_lower = budget_str.lower()
    
    # Common currency patterns (order matters - more specific first)
    currency_patterns = {
        'sri lankan rupees': 'Rs',
        'pakistani rupees': 'PKR',
        'indian rupees': 'INR',
        'nepalese rupees': 'NPR',
        'us dollars': 'USD',
        'american dollars': 'USD',
        'rupees': 'Rs',  # Generic rupees - after specific ones
        'dollars': 'USD',  # Generic dollars - after specific ones
        'rs': 'Rs',
        'lkr': 'Rs', 
        'usd': 'USD',
        'us$': 'USD', 
        '$': 'USD',
        'eur': 'EUR',
        '€': 'EUR',
        'euros': 'EUR',
        'gbp': 'GBP',
        '£': 'GBP',
        'pounds': 'GBP',
        'inr': 'INR',
        '₹': 'INR',
        'indian rupees': 'INR',
        'aud': 'AUD',
        'cad': 'CAD',
        'jpy': 'JPY',
        '¥': 'JPY',
        'yen': 'JPY',
        'cny': 'CNY',
        'yuan': 'CNY',
        'sgd': 'SGD',
        'hkd': 'HKD',
        'thb': 'THB',
        'baht': 'THB',
        'myr': 'MYR',
        'ringgit': 'MYR',
        'pkr': 'PKR',
        'pakistani rupees': 'PKR',
        'bdt': 'BDT',
        'taka': 'BDT',
        'npr': 'NPR',
        'nepalese rupees': 'NPR'
    }
    
    for pattern, currency in currency_patterns.items():
        if pattern in budget_lower:
            return currency
    
    # Default to Rs if no currency detected
    return 'Rs'

def clean_budget_amount(budget_text):
    """Extract numeric amount from budget text"""
    import pandas as pd
    
    if pd.isna(budget_text) or budget_text == '':
        return None
    
    budget_str = str(budget_text).strip()
    
    # Remove common currency symbols and words
    remove_patterns = [
        'rs', 'lkr', 'usd', 'us$', '$', 'eur', '€', 'gbp', '£', 
        'inr', '₹', 'aud', 'cad', 'jpy', '¥', 'cny', 'sgd', 'hkd', 
        'thb', 'myr', 'pkr', 'bdt', 'npr', 'rupees', 'dollars', 
        'euros', 'pounds', 'yen', 'yuan', 'baht', 'ringgit', 'taka'
    ]
    
    # Clean the text
    clean_text = budget_str.lower()
    for pattern in remove_patterns:
        clean_text = clean_text.replace(pattern, '')
    
    # Remove non-numeric characters except decimal point and comma
    import re
    clean_text = re.sub(r'[^\d.,]', '', clean_text)
    
    # Handle comma as thousands separator
    clean_text = clean_text.replace(',', '')
    
    try:
        return float(clean_text) if clean_text else None
    except ValueError:
        return None

def generate_unique_project_ids_for_batch(projects):
    """Generate unique project IDs for a batch of projects - use start_date first, then end_date, then 0000 for bulk import"""
    # Group projects by year
    projects_by_year = {}
    for project in projects:
        # For bulk import: use start_date first, then end_date, then "0000" as default
        if project.start_date:
            year = project.start_date.year
        elif project.end_date:
            year = project.end_date.year
        else:
            year = "0000"  # Use 0000 as default for bulk import when no dates available
        
        if year not in projects_by_year:
            projects_by_year[year] = []
        projects_by_year[year].append(project)
    
    # Generate unique IDs for each year
    for year, year_projects in projects_by_year.items():
        # Find the highest existing project number for this year
        existing_projects = Project.query.filter(
            Project.project_id.like(f'PROJ-{year}-%')
        ).all()
        
        if not existing_projects:
            start_number = 1
        else:
            # Extract numbers from existing project IDs and find the highest
            numbers = []
            for project in existing_projects:
                try:
                    parts = project.project_id.split('-')
                    if len(parts) == 3 and parts[0] == 'PROJ' and parts[1] == str(year):
                        numbers.append(int(parts[2]))
                except (ValueError, IndexError):
                    continue
            
            start_number = max(numbers) + 1 if numbers else 1
        
        # Assign sequential IDs to projects in this year
        for i, project in enumerate(year_projects):
            project_number = start_number + i
            project.project_id = f"PROJ-{year}-{project_number:03d}"

def check_project_duplicate(title, start_date_str, end_date_str):
    """
    Check if a project is a duplicate based on title and dates.
    Returns True if duplicate (same title and similar dates), False otherwise.
    """
    # Find projects with the same title
    existing_projects = Project.query.filter_by(title=title.strip()).all()
    
    if not existing_projects:
        return False
    
    # Parse incoming dates
    new_start_date = None
    new_end_date = None
    
    if start_date_str:
        try:
            new_start_date = pd.to_datetime(start_date_str).date()
        except:
            pass
    
    if end_date_str:
        try:
            new_end_date = pd.to_datetime(end_date_str).date()
        except:
            pass
    
    # Check each existing project
    for existing in existing_projects:
        dates_similar = True
        
        # Compare start dates
        if new_start_date and existing.start_date:
            days_diff = abs((new_start_date - existing.start_date).days)
            if days_diff > 30:  # More than 30 days difference
                dates_similar = False
        elif new_start_date or existing.start_date:
            # One has start date, other doesn't - consider different unless both are None
            if new_start_date != existing.start_date:
                dates_similar = False
        
        # Compare end dates
        if new_end_date and existing.end_date:
            days_diff = abs((new_end_date - existing.end_date).days)
            if days_diff > 30:  # More than 30 days difference
                dates_similar = False
        elif new_end_date or existing.end_date:
            # One has end date, other doesn't - consider different unless both are None
            if new_end_date != existing.end_date:
                dates_similar = False
        
        # If dates are similar, consider it a duplicate
        if dates_similar:
            return True
    
    return False

def normalize_status_value(status_value):
    """Normalize status value to match valid status options"""
    if not status_value:
        return 'Active'  # Default status
    
    # Convert to string and normalize
    status_str = str(status_value).strip()
    status_lower = status_str.lower()
    
    # Valid statuses (case-insensitive mapping)
    status_mapping = {
        'active': 'Active',
        'on hold': 'On Hold',
        'onhold': 'On Hold',
        'hold': 'On Hold',
        'paused': 'On Hold',
        'completed': 'Completed',
        'complete': 'Completed',
        'finished': 'Completed',
        'done': 'Completed',
        'cancelled': 'Cancelled',
        'canceled': 'Cancelled',  # American spelling
        'terminated': 'Cancelled',
        'stopped': 'Cancelled',
        'abandoned': 'Cancelled'
    }
    
    # Try exact match first
    if status_lower in status_mapping:
        return status_mapping[status_lower]
    
    # Try partial matches
    for key, value in status_mapping.items():
        if key in status_lower or status_lower in key:
            return value
    
    # If no match found, default to Active
    print(f"Warning: Unknown status '{status_str}' found in import, defaulting to 'Active'")
    return 'Active'

def process_import_data(df, skip_duplicates=False):
    """Process imported DataFrame and create Project objects"""
    processed_projects = []
    
    # Column mapping (flexible column names)
    column_mapping = {
        'title': ['title', 'project title', 'name', 'project name'],
        'principal_investigator': ['principal investigator', 'pi', 'lead', 'principal_investigator'],
        'description': ['description', 'desc', 'summary', 'abstract'],
        'category': ['category', 'project category', 'type', 'field'],
        'theme': ['theme', 'project theme', 'subject', 'topic'],
        'status': ['status', 'project status', 'state'],
        'start_date': ['start date', 'start_date', 'begin date', 'commencement'],
        'end_date': ['end date', 'end_date', 'finish date', 'completion'],
        'team_members': ['team members', 'team_members', 'team', 'members'],
        'funding_source': ['funding source', 'funding_source', 'funder', 'sponsor'],
        'budget': ['budget', 'amount', 'funding amount'],
        'currency': ['currency', 'curr', 'money type']
    }
    
    # Find actual column names in the DataFrame
    df_columns = {col.lower().strip(): col for col in df.columns}
    mapped_columns = {}
    
    for field, possible_names in column_mapping.items():
        for name in possible_names:
            if name.lower() in df_columns:
                mapped_columns[field] = df_columns[name.lower()]
                break
    
    for index, row in df.iterrows():
        try:
            # Extract data using mapped columns
            title = row.get(mapped_columns.get('title', ''), '').strip() if mapped_columns.get('title') else ''
            pi = row.get(mapped_columns.get('principal_investigator', ''), '').strip() if mapped_columns.get('principal_investigator') else ''
            
            # Skip if no title or PI
            if not title or not pi:
                continue
            
            # Check for duplicates if requested (enhanced checking with dates)
            if skip_duplicates:
                is_duplicate = check_project_duplicate(title, 
                                                     row.get(mapped_columns.get('start_date', ''), ''),
                                                     row.get(mapped_columns.get('end_date', ''), ''))
                if is_duplicate:
                    continue
            
            # Create project object
            project = Project()
            project.title = title
            project.principal_investigator = pi
            project.description = row.get(mapped_columns.get('description', ''), '') or 'Not specified'
            project.category = row.get(mapped_columns.get('category', ''), '') or None
            project.theme = row.get(mapped_columns.get('theme', ''), '') or None
            
            # Handle status with validation and normalization
            raw_status = row.get(mapped_columns.get('status', ''), 'Active') or 'Active'
            project.status = normalize_status_value(raw_status)
            
            project.team_members = row.get(mapped_columns.get('team_members', ''), '') or ''
            project.funding_source = row.get(mapped_columns.get('funding_source', ''), '') or ''
            
            # Handle budget and currency intelligently
            budget_val = row.get(mapped_columns.get('budget', ''), '')
            currency_val = row.get(mapped_columns.get('currency', ''), '')
            
            # Detect currency from budget text and currency column
            project.currency = detect_currency_from_budget(budget_val, currency_val)
            
            # Clean and extract numeric budget amount
            project.budget = clean_budget_amount(budget_val)
            
            # Handle dates
            project.start_date = parse_date_flexible(row.get(mapped_columns.get('start_date', ''), ''))
            project.end_date = parse_date_flexible(row.get(mapped_columns.get('end_date', ''), ''))
            
            # Don't generate project ID yet - will be done in batch
            project.created_at = datetime.utcnow()  # Use UTC for consistency
            
            processed_projects.append(project)
            
        except Exception as e:
            print(f"Error processing row {index}: {e}")
            continue
    
    # Generate unique project IDs for the entire batch
    generate_unique_project_ids_for_batch(processed_projects)
    
    return processed_projects

def parse_date_flexible(date_value):
    """Parse date from various formats"""
    import pandas as pd
    
    if pd.isna(date_value) or date_value == '' or date_value is None:
        return None
    
    # If it's already a datetime object
    if isinstance(date_value, datetime):
        return date_value.date()
    
    # Convert to string and try various formats
    date_str = str(date_value).strip()
    
    date_formats = [
        '%Y-%m-%d',     # 2024-12-31
        '%d/%m/%Y',     # 31/12/2024
        '%m/%d/%Y',     # 12/31/2024
        '%d-%m-%Y',     # 31-12-2024
        '%Y/%m/%d',     # 2024/12/31
        '%d.%m.%Y',     # 31.12.2024
        '%B %d, %Y',    # December 31, 2024
        '%b %d, %Y',    # Dec 31, 2024
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None

def import_projects_to_db(projects):
    """Import processed projects to database and return results"""
    results = {
        'success_count': 0,
        'error_count': 0,
        'skipped_count': 0,
        'total_processed': len(projects),
        'errors': []
    }
    
    for project in projects:
        try:
            # Check for duplicates one more time (enhanced checking with dates)
            is_duplicate = check_project_duplicate(project.title, 
                                                 project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
                                                 project.end_date.strftime('%Y-%m-%d') if project.end_date else '')
            if is_duplicate:
                results['skipped_count'] += 1
                continue
            
            db.session.add(project)
            db.session.commit()
            results['success_count'] += 1
            
        except Exception as e:
            db.session.rollback()
            results['error_count'] += 1
            results['errors'].append(f"Project '{project.title}': {str(e)}")
    
    return results

@app.route('/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    """User management - only for full access users"""
    if not current_user.can_edit_projects():
        flash('Access denied. Full access privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            username = request.form['username'].strip()
            password = request.form['password']
            full_name = request.form['full_name'].strip()
            role = request.form['role']
            
            # Validate role
            valid_roles = ['full_access', 'view_all', 'view_limited']
            if role not in valid_roles:
                flash('Invalid role selected.', 'error')
                return redirect(url_for('manage_users'))
            
            # Check if username already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'error')
                return redirect(url_for('manage_users'))
            
            # Create new user
            from werkzeug.security import generate_password_hash
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                full_name=full_name,
                role=role
            )
            
            db.session.add(user)
            db.session.commit()
            
            flash(f'User "{username}" created successfully with {User.query.get(user.id).get_role_display()} access.', 'success')
            return redirect(url_for('manage_users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'error')
    
    # Get all users
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('manage_users.html', users=users)

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit user details"""
    if not current_user.can_edit_projects():
        flash('Access denied. Full access privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            # Don't allow editing of username (to avoid conflicts)
            user.full_name = request.form['full_name'].strip()
            role = request.form['role']
            
            # Validate role
            valid_roles = ['full_access', 'view_all', 'view_limited']
            if role not in valid_roles:
                flash('Invalid role selected.', 'error')
                return redirect(url_for('edit_user', user_id=user_id))
            
            user.role = role
            
            # Change password if provided
            new_password = request.form.get('new_password', '').strip()
            if new_password:
                from werkzeug.security import generate_password_hash
                user.password_hash = generate_password_hash(new_password)
            
            db.session.commit()
            flash(f'User "{user.username}" updated successfully.', 'success')
            return redirect(url_for('manage_users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    
    return render_template('edit_user.html', user=user)

@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete user (with safety checks)"""
    if not current_user.can_edit_projects():
        flash('Access denied. Full access privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deletion of current user
    if user.id == current_user.id:
        flash('Cannot delete your own account.', 'error')
        return redirect(url_for('manage_users'))
    
    # Prevent deletion if it would leave no full access users
    full_access_users = User.query.filter_by(role='full_access').count()
    if user.role == 'full_access' and full_access_users <= 1:
        flash('Cannot delete the last full access user. At least one full access user must remain.', 'error')
        return redirect(url_for('manage_users'))
    
    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f'User "{username}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('manage_users'))

@app.route('/users/reset-password/<int:user_id>', methods=['POST'])
@login_required
def reset_user_password(user_id):
    """Reset user password to a temporary password"""
    if not current_user.can_edit_projects():
        flash('Access denied. Full access privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    try:
        # Generate temporary password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        
        from werkzeug.security import generate_password_hash
        user.password_hash = generate_password_hash(temp_password)
        db.session.commit()
        
        flash(f'Password reset for "{user.username}". Temporary password: {temp_password}', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error resetting password: {str(e)}', 'error')
    
    return redirect(url_for('manage_users'))

@app.route('/admin/backup')
@login_required
def backup_system():
    """System backup and maintenance page"""
    if not current_user.can_edit_projects():
        flash('Access denied. Full access privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get backup directory info
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # List existing backups
    backups = []
    if os.path.exists(backup_dir):
        for file in os.listdir(backup_dir):
            if file.endswith('.db') or file.endswith('.sql'):
                file_path = os.path.join(backup_dir, file)
                file_size = os.path.getsize(file_path)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                backups.append({
                    'filename': file,
                    'size': file_size,
                    'created': file_time,
                    'size_mb': round(file_size / 1024 / 1024, 2)
                })
    
    backups.sort(key=lambda x: x['created'], reverse=True)
    
    # Get database stats
    project_count = Project.query.count()
    user_count = User.query.count()
    
    return render_template('backup_system.html', 
                         backups=backups, 
                         project_count=project_count, 
                         user_count=user_count)

@app.route('/admin/backup/create', methods=['POST'])
@login_required
def create_backup():
    """Create a database backup"""
    if not current_user.can_edit_projects():
        flash('Access denied. Full access privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        import shutil
        from datetime import datetime
        
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Create timestamp for backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Get current database path
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'research_projects.db')
        
        # Create backup filename
        backup_filename = f'backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy database file
        shutil.copy2(db_path, backup_path)
        
        # Also create an SQL dump for extra safety
        sql_filename = f'backup_{timestamp}.sql'
        sql_path = os.path.join(backup_dir, sql_filename)
        
        # Create SQL dump
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            with open(sql_path, 'w') as f:
                for line in conn.iterdump():
                    f.write('%s\n' % line)
        
        flash(f'Backup created successfully: {backup_filename}', 'success')
        
    except Exception as e:
        flash(f'Error creating backup: {str(e)}', 'error')
    
    return redirect(url_for('backup_system'))

@app.route('/admin/backup/download/<filename>')
@login_required
def download_backup(filename):
    """Download a backup file"""
    if not current_user.can_edit_projects():
        flash('Access denied. Full access privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        file_path = os.path.join(backup_dir, filename)
        
        # Security check - ensure file is in backup directory
        if not os.path.exists(file_path) or not file_path.startswith(backup_dir):
            flash('Backup file not found.', 'error')
            return redirect(url_for('backup_system'))
        
        from flask import send_file
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        flash(f'Error downloading backup: {str(e)}', 'error')
        return redirect(url_for('backup_system'))

@app.route('/admin/backup/restore/<filename>', methods=['POST'])
@login_required
def restore_backup(filename):
    """Restore from a backup file"""
    if not current_user.can_edit_projects():
        flash('Access denied. Full access privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        import shutil
        
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        backup_path = os.path.join(backup_dir, filename)
        
        # Security check
        if not os.path.exists(backup_path) or not backup_path.startswith(backup_dir):
            flash('Backup file not found.', 'error')
            return redirect(url_for('backup_system'))
        
        # Only restore .db files (not .sql files)
        if not filename.endswith('.db'):
            flash('Can only restore .db backup files directly.', 'error')
            return redirect(url_for('backup_system'))
        
        # Create a backup of current database before restoring
        current_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'research_projects.db')
        current_backup_path = os.path.join(backup_dir, f'current_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        shutil.copy2(current_db_path, current_backup_path)
        
        # Restore the backup
        shutil.copy2(backup_path, current_db_path)
        
        # Clear the SQLAlchemy session to reload data
        db.session.remove()
        
        flash(f'Database restored from {filename}. Current database backed up as {os.path.basename(current_backup_path)}.', 'success')
        flash('Please restart the application for changes to take full effect.', 'warning')
        
    except Exception as e:
        flash(f'Error restoring backup: {str(e)}', 'error')
    
    return redirect(url_for('backup_system'))

@app.route('/admin/backup/delete/<filename>', methods=['POST'])
@login_required
def delete_backup(filename):
    """Delete a backup file"""
    if not current_user.can_edit_projects():
        flash('Access denied. Full access privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        file_path = os.path.join(backup_dir, filename)
        
        # Security check
        if not os.path.exists(file_path) or not file_path.startswith(backup_dir):
            flash('Backup file not found.', 'error')
            return redirect(url_for('backup_system'))
        
        os.remove(file_path)
        flash(f'Backup {filename} deleted successfully.', 'success')
        
    except Exception as e:
        flash(f'Error deleting backup: {str(e)}', 'error')
    
    return redirect(url_for('backup_system'))

@app.route('/test-features')
@login_required
def test_features():
    """Diagnostic page to show implemented features"""
    features_status = {
        'User Management': {
            'route': '/users',
            'description': 'Add, edit, delete users and manage passwords',
            'accessible': current_user.can_edit_projects()
        },
        'Backup System': {
            'route': '/admin/backup',
            'description': 'Create, download, and restore database backups',
            'accessible': current_user.can_edit_projects()
        },
        'Password Reset': {
            'route': '/forgot-password',
            'description': 'Reset forgotten passwords',
            'accessible': True
        },
        'Change Password': {
            'route': '/change-password',
            'description': 'Change your own password',
            'accessible': True
        },
        'Enhanced Dashboard': {
            'route': '/dashboard',
            'description': 'Admin dashboard with system monitoring',
            'accessible': True
        }
    }
    
    return f"""
    <html>
    <head><title>Feature Test - Marga Institute</title></head>
    <body style="font-family: Arial; margin: 40px;">
        <h1>🚀 New Features Status</h1>
        <p><strong>Logged in as:</strong> {current_user.full_name} ({current_user.get_role_display()})</p>
        
        <h2>✅ Implemented Features:</h2>
        <ul>
        {''.join([f'<li><strong>{name}:</strong> {info["description"]}<br>'
                 f'<a href="{info["route"]}" style="color: {"green" if info["accessible"] else "red"};">'
                 f'{"✅ Access " + info["route"] if info["accessible"] else "❌ Not accessible with your role"}</a></li><br>'
                 for name, info in features_status.items()])}
        </ul>
        
        <h2>🔧 Troubleshooting:</h2>
        <ol>
            <li>Try hard refresh (Ctrl+F5) to clear browser cache</li>
            <li>Check navigation bar for new "Users", "Backup", "Change Password" links</li>
            <li>Log in as <strong>manager/manager123</strong> to see admin features</li>
            <li>Visit <a href="/dashboard">enhanced dashboard</a> for new admin sections</li>
        </ol>
        
        <p><a href="/dashboard">← Back to Dashboard</a></p>
    </body>
    </html>
    """

@app.route('/error-logs')
@login_required
def error_logs():
    """View error logs (admin only)"""
    if not current_user.can_edit_projects():
        flash('Access denied. Administrator privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    severity_filter = request.args.get('severity', '')
    resolved_filter = request.args.get('resolved', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = ErrorLog.query
    
    if severity_filter:
        query = query.filter(ErrorLog.severity == severity_filter)
    
    if resolved_filter:
        is_resolved = resolved_filter.lower() == 'true'
        query = query.filter(ErrorLog.resolved == is_resolved)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(ErrorLog.occurred_at >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(ErrorLog.occurred_at < date_to_obj)
        except ValueError:
            pass
    
    # Order by most recent first and paginate
    errors = query.order_by(ErrorLog.occurred_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    
    # Get available severities for filter dropdown
    available_severities = ['error', 'warning', 'critical']
    
    return render_template('error_logs.html', 
                         errors=errors, 
                         available_severities=available_severities,
                         filters={
                             'severity': severity_filter,
                             'resolved': resolved_filter,
                             'date_from': date_from,
                             'date_to': date_to
                         })

@app.route('/error-logs/<int:id>/resolve', methods=['POST'])
@login_required
def resolve_error(id):
    """Mark an error as resolved"""
    if not current_user.can_edit_projects():
        flash('Access denied. Administrator privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    error_log = ErrorLog.query.get_or_404(id)
    error_log.resolved = True
    
    try:
        db.session.commit()
        log_user_activity('resolve_error', 'error_log', str(id), {
            'error_type': error_log.error_type,
            'error_message': error_log.error_message[:100]
        })
        flash('Error marked as resolved.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to resolve error.', 'error')
    
    return redirect(url_for('error_logs'))

@app.route('/audit-logs')
@login_required
def audit_logs():
    """View audit logs (admin only)"""
    if not current_user.can_edit_projects():
        flash('Access denied. Administrator privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    user_filter = request.args.get('user', '')
    action_filter = request.args.get('action', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = AuditLog.query
    
    if user_filter:
        query = query.join(User).filter(User.username.ilike(f'%{user_filter}%'))
    
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f'%{action_filter}%'))
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AuditLog.timestamp >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditLog.timestamp < date_to_obj)
        except ValueError:
            pass
    
    # Order by most recent first and paginate
    logs = query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # Get available actions for filter dropdown
    available_actions = db.session.query(AuditLog.action.distinct()).all()
    available_actions = [action[0] for action in available_actions]
    
    return render_template('audit_logs.html', 
                         logs=logs, 
                         available_actions=available_actions,
                         filters={
                             'user': user_filter,
                             'action': action_filter,
                             'date_from': date_from,
                             'date_to': date_to
                         })

@app.route('/api/search/projects')
@login_required
def api_search_projects():
    """API endpoint for advanced project search with JSON response"""
    try:
        # Get search parameters
        query = request.args.get('q', '').strip()
        fields = request.args.getlist('fields')  # Fields to search in
        limit = min(int(request.args.get('limit', 10)), 50)  # Max 50 results
        
        # Default fields if none specified
        if not fields:
            fields = ['title', 'description', 'principal_investigator', 'project_id']
        
        # Build search query
        search_query = Project.query
        
        if query:
            search_conditions = []
            search_pattern = f'%{query}%'
            
            if 'title' in fields:
                search_conditions.append(Project.title.ilike(search_pattern))
            if 'description' in fields:
                search_conditions.append(Project.description.ilike(search_pattern))
            if 'principal_investigator' in fields:
                search_conditions.append(Project.principal_investigator.ilike(search_pattern))
            if 'project_id' in fields:
                search_conditions.append(Project.project_id.ilike(search_pattern))
            if 'team_members' in fields:
                search_conditions.append(Project.team_members.ilike(search_pattern))
            if 'category' in fields:
                search_conditions.append(Project.category.ilike(search_pattern))
            if 'theme' in fields:
                search_conditions.append(Project.theme.ilike(search_pattern))
            
            if search_conditions:
                search_query = search_query.filter(db.or_(*search_conditions))
        
        # Execute search and limit results
        projects = search_query.order_by(Project.updated_at.desc()).limit(limit).all()
        
        # Format results
        results = []
        for project in projects:
            results.append({
                'id': project.id,
                'project_id': project.project_id,
                'title': project.title,
                'principal_investigator': project.principal_investigator,
                'status': project.status,
                'category': project.category,
                'theme': project.theme,
                'start_date': project.start_date.isoformat() if project.start_date else None,
                'budget': float(project.budget) if project.budget else None,
                'currency': project.currency,
                'url': url_for('view_project', id=project.id)
            })
        
        return {
            'status': 'success',
            'query': query,
            'fields': fields,
            'count': len(results),
            'results': results
        }, 200
        
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }, 500

@app.route('/session/extend', methods=['POST'])
@login_required
def extend_session():
    """Extend user session"""
    try:
        session['last_activity'] = datetime.now().isoformat()
        session.permanent = True
        
        # Log session extension
        log_user_activity('session_extended', 'system', None, {'method': 'manual'})
        
        return {'status': 'success', 'message': 'Session extended successfully'}, 200
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/session/status')
@login_required
def session_status():
    """Get current session status"""
    try:
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            timeout_duration = app.config['PERMANENT_SESSION_LIFETIME']
            time_left = timeout_duration - (datetime.now() - last_activity)
            
            return {
                'status': 'active',
                'time_left_seconds': int(time_left.total_seconds()),
                'timeout_minutes': int(timeout_duration.total_seconds() / 60)
            }, 200
        else:
            return {'status': 'no_activity_tracking'}, 200
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/health')
def health_check():
    """Health check endpoint for load balancers and monitoring"""
    try:
        # Check database connectivity
        db.session.execute('SELECT 1')
        
        # Return health status
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'Marga Research Institute Management System',
            'version': '1.0.0'
        }, 200
    except Exception as e:
        return {
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }, 503

@app.route('/clear-all-projects', methods=['POST'])
@login_required
def clear_all_projects():
    """Clear all projects from the database - ADMIN ONLY"""
    if not current_user.can_edit_projects():
        flash('Access denied. Full access privileges required.', 'error')
        return redirect(url_for('projects'))
    
    try:
        # Get count before deletion
        project_count = Project.query.count()
        
        # Delete all projects
        Project.query.delete()
        db.session.commit()
        
        # Log the action
        log_user_activity('bulk_delete', 'project', 'all', {
            'action': 'cleared_all_projects',
            'count': project_count,
            'reason': 'Fresh import preparation'
        })
        
        flash(f'Successfully deleted {project_count} projects from the database.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error clearing projects: {str(e)}', 'error')
    
    return redirect(url_for('projects'))

if __name__ == '__main__':
    print("="*50)
    print("Starting Marga Research Institute Management System")
    print("Server URL: http://127.0.0.1:5000")
    print("="*50)
    print("Available Login Accounts:")
    print("Manager (Full Access):     manager / manager123")
    print("Researcher (View All):     researcher / researcher123") 
    print("Assistant (View Limited):  assistant / assistant123")
    print("="*50)
    app.run(debug=True, host='127.0.0.1', port=5000)
