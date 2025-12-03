# utils.py - Utility functions

import csv
import json
import io
from datetime import datetime
from functools import wraps
from flask import jsonify, request, current_app
import re
from models import APIKey, User, db
from werkzeug.security import check_password_hash

# ============================================================================
# Export Functions
# ============================================================================

def export_leads_to_csv(leads):
    """
    Export leads to CSV format
    Returns: StringIO object containing CSV data
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'ID', 'Username', 'Platform', 'Full Name', 'Bio', 'Followers',
        'Email', 'Website', 'Location', 'Profile URL', 'Engagement Score',
        'Tags', 'Created At', 'Last Updated'
    ])
    
    # Write data
    for lead in leads:
        writer.writerow([
            lead.id,
            lead.username,
            lead.platform,
            lead.full_name or '',
            lead.bio or '',
            lead.followers,
            lead.email or '',
            lead.website or '',
            lead.location or '',
            lead.profile_url or '',
            lead.engagement_score,
            ', '.join(lead.tags_list),
            lead.created_at.strftime('%Y-%m-%d %H:%M:%S') if lead.created_at else '',
            lead.last_updated.strftime('%Y-%m-%d %H:%M:%S') if lead.last_updated else ''
        ])
    
    output.seek(0)
    return output


def export_leads_to_json(leads):
    """
    Export leads to JSON format
    Returns: JSON string
    """
    leads_data = [lead.to_dict() for lead in leads]
    return json.dumps(leads_data, indent=2)


# ============================================================================
# Import Functions
# ============================================================================

def parse_csv_file(file_content):
    """
    Parse CSV file content and return list of lead dictionaries
    """
    leads_data = []
    
    # Decode if bytes
    if isinstance(file_content, bytes):
        file_content = file_content.decode('utf-8')
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(file_content))

    def _get_stripped_value(row_data, key, default=''):
        return str(row_data.get(key, default)).strip()

    for row in csv_reader:
        if not row:  # Skip empty rows
            continue

        lead_data = {
            'username': _get_stripped_value(row, 'username'),
            'platform': _get_stripped_value(row, 'platform').lower(),
            'full_name': _get_stripped_value(row, 'full_name') or None,
            'bio': _get_stripped_value(row, 'bio') or None,
            'followers': int(_get_stripped_value(row, 'followers', '0')) if _get_stripped_value(row, 'followers', '0').isdigit() else 0,
            'email': _get_stripped_value(row, 'email') or None,
            'website': _get_stripped_value(row, 'website') or None,
            'location': _get_stripped_value(row, 'location') or None,
            'profile_url': _get_stripped_value(row, 'profile_url') or None,
            'engagement_score': float(_get_stripped_value(row, 'engagement_score', '0.0')) if _get_stripped_value(row, 'engagement_score', '0.0').replace('.', '', 1).isdigit() else 0.0,
            'tags': _get_stripped_value(row, 'tags') or '[]',
            'company_name': _get_stripped_value(row, 'company_name') or None,
            'company_industry': _get_stripped_value(row, 'company_industry') or None,
            'company_size': _get_stripped_value(row, 'company_size') or None,
            'job_title': _get_stripped_value(row, 'job_title') or None,
            'tech_stack': json.dumps([t.strip() for t in _get_stripped_value(row, 'tech_stack').split(',') if t.strip()]) if _get_stripped_value(row, 'tech_stack') else '[]'
        }

        if lead_data['username'] and lead_data['platform']:
            leads_data.append(lead_data)
    
    return leads_data


def parse_json_file(file_content):
    """
    Parse JSON file content and return list of lead dictionaries
    """
    # Decode if bytes
    if isinstance(file_content, bytes):
        file_content = file_content.decode('utf-8')
    
    data = json.loads(file_content)
    
    # Handle both array and object with 'leads' key
    if isinstance(data, dict) and 'leads' in data:
        data = data['leads']
    
    if not isinstance(data, list):
        raise ValueError("JSON must contain an array of leads")
    
    return data


# ============================================================================
# Validation Functions
# ============================================================================

def validate_email(email):
    """Validate email format"""
    if not email:
        return True  # Empty email is allowed
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_url(url):
    """Validate URL format"""
    if not url:
        return True  # Empty URL is allowed
    
    pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    return re.match(pattern, url) is not None


def sanitize_input(text):
    """Sanitize user input to prevent XSS"""
    if not text:
        return text
    
    # Remove potential HTML tags
    text = re.sub(r'<[^>]*>', '', str(text))
    
    # Remove potential script tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    return text.strip()


# ============================================================================
# Data Processing Functions
# ============================================================================

def format_number(num):
    """Format large numbers with commas"""
    if num is None:
        return '0'
    return '{:,}'.format(int(num))


def format_percentage(value):
    """Format value as percentage"""
    if value is None:
        return '0%'
    return f'{value:.2f}%'


def calculate_growth_percentage(current, previous):
    """Calculate percentage growth"""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    
    return ((current - previous) / previous) * 100


def truncate_text(text, max_length=100, suffix='...'):
    """Truncate text to specified length"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


# ============================================================================
# Date/Time Functions
# ============================================================================

def format_datetime(dt, format='%Y-%m-%d %H:%M:%S'):
    """Format datetime object to string"""
    if not dt:
        return ''
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except:
            return dt
    
    return dt.strftime(format)


def format_relative_time(dt):
    """Format datetime as relative time (e.g., '2 hours ago')"""
    if not dt:
        return ''
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except:
            return dt
    
    now = datetime.utcnow()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours} hour{"s" if hours != 1 else ""} ago'
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f'{days} day{"s" if days != 1 else ""} ago'
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f'{weeks} week{"s" if weeks != 1 else ""} ago'
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f'{months} month{"s" if months != 1 else ""} ago'
    else:
        years = int(seconds / 31536000)
        return f'{years} year{"s" if years != 1 else ""} ago'


# ============================================================================
# API Helper Functions
# ============================================================================

def create_response(data=None, message=None, status=200, error=None):
    """Create standardized API response"""
    response = {
        'success': status < 400,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if message:
        response['message'] = message
    
    if data is not None:
        response['data'] = data
    
    if error:
        response['error'] = error
    
    return jsonify(response), status


def paginate_results(query, page=1, per_page=20):
    """
    Paginate query results
    Returns: (items, pagination_info)
    """
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    pagination_info = {
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
        'has_prev': pagination.has_prev,
        'has_next': pagination.has_next,
        'prev_page': pagination.prev_num,
        'next_page': pagination.next_num
    }
    
    return pagination.items, pagination_info


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, identifier, limit=100, window=3600):
        """
        Check if request is allowed
        identifier: IP address or API key
        limit: Max requests per window
        window: Time window in seconds
        """
        now = datetime.utcnow().timestamp()
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Remove old requests outside the window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < window
        ]
        
        # Check if limit exceeded
        if len(self.requests[identifier]) >= limit:
            return False
        
        # Add current request
        self.requests[identifier].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


def require_api_key(f):
    """Decorator to require API key for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return create_response(
                error='API key is required',
                status=401
            )
        
        # Validate the API key against the database
        api_key_obj = APIKey.query.filter_by(key=api_key, is_active=True).first()

        if not api_key_obj or (api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow()):
            return create_response(
                error='Invalid or expired API key',
                status=401
            )
        
        # Attach the user associated with the API key to the request context
        # This allows routes to access current_user for API requests
        request.api_user = api_key_obj.user
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_rate_limit(limit=100, window=3600):
    """Decorator to enforce rate limiting"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identifier = request.remote_addr
            
            if not rate_limiter.is_allowed(identifier, limit, window):
                return create_response(
                    error='Rate limit exceeded',
                    status=429
                )
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


# ============================================================================
# File Upload Helpers
# ============================================================================

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def secure_filename(filename):
    """Sanitize filename"""
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove potentially dangerous characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    
    return filename or 'file'