from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import os

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and role management"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def can_edit_projects(self):
        """Check if user can add, edit, or delete projects"""
        return self.role == 'full_access'
    
    def can_view_budget(self):
        """Check if user can view budget information"""
        return self.role in ['full_access', 'view_all']
    
    def can_view_projects(self):
        """Check if user can view projects (all users can)"""
        return True
    
    def get_role_display(self):
        """Get human-readable role name"""
        role_names = {
            'full_access': 'Full Access',
            'view_all': 'View All',
            'view_limited': 'View Limited'
        }
        return role_names.get(self.role, 'Unknown')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Project(db.Model):
    """Project model for research project management"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=True)  # Allow NULL for missing dates
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='Active')
    principal_investigator = db.Column(db.String(100), nullable=False)
    team_members = db.Column(db.Text)
    budget = db.Column(db.Numeric(12, 2))
    currency = db.Column(db.String(10), default='Rs')
    funding_source = db.Column(db.String(100))
    category = db.Column(db.String(100))  # New column for project category
    theme = db.Column(db.String(100))     # New column for project theme
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Project {self.project_id}: {self.title}>'

class AuditLog(db.Model):
    """Audit log model for tracking user activities"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # login, logout, create_project, edit_project, etc.
    resource_type = db.Column(db.String(50))  # project, user, system, etc.
    resource_id = db.Column(db.String(100))  # ID of the affected resource
    details = db.Column(db.Text)  # JSON string with additional details
    ip_address = db.Column(db.String(45))  # Support both IPv4 and IPv6
    user_agent = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))
    
    def __repr__(self):
        return f'<AuditLog {self.user.username}: {self.action} at {self.timestamp}>'
    
    def get_details_dict(self):
        """Parse details JSON string to dictionary"""
        if self.details:
            try:
                import json
                return json.loads(self.details)
            except:
                return {}
        return {}

class ProjectStatusHistory(db.Model):
    """Track project status changes over time"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    from_status = db.Column(db.String(20))  # Previous status (null for initial status)
    to_status = db.Column(db.String(20), nullable=False)  # New status
    reason = db.Column(db.Text)  # Optional reason for status change
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('status_history', lazy=True, order_by='ProjectStatusHistory.changed_at.desc()'))
    user = db.relationship('User', backref=db.backref('status_changes', lazy=True))
    
    def __repr__(self):
        return f'<StatusChange {self.project.project_id}: {self.from_status} -> {self.to_status}>'

class ErrorLog(db.Model):
    """Log application errors for monitoring and debugging"""
    id = db.Column(db.Integer, primary_key=True)
    error_type = db.Column(db.String(100), nullable=False)
    error_message = db.Column(db.Text, nullable=False)
    traceback = db.Column(db.Text)
    context = db.Column(db.Text)  # JSON string with additional context
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    url = db.Column(db.String(500))
    method = db.Column(db.String(10))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    severity = db.Column(db.String(20), default='error')  # error, warning, critical
    resolved = db.Column(db.Boolean, default=False)
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('error_logs', lazy=True))
    
    def __repr__(self):
        return f'<ErrorLog {self.error_type}: {self.error_message[:50]}...>'
    
    def get_context_dict(self):
        """Parse context JSON string to dictionary"""
        if self.context:
            try:
                import json
                return json.loads(self.context)
            except:
                return {}
        return {}

def init_database(app):
    """Initialize database with tables and default data"""
    with app.app_context():
        db.create_all()
        
        # Create default admin user if no users exist
        if User.query.count() == 0:
            from werkzeug.security import generate_password_hash
            
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                full_name='System Administrator',
                role='admin'
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created (username: admin, password: admin123)")
