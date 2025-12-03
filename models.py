# models.py - Database models and operations

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """User model for authentication"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    member_since = db.Column(db.DateTime, default=datetime.utcnow)
    
    leads = db.relationship('Lead', backref='owner', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Lead(db.Model):
    """Lead model for storing social media contact information"""
    
    __tablename__ = 'leads'
    
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    username = db.Column(db.String(100), nullable=False, index=True)
    platform = db.Column(db.String(50), nullable=False, index=True)
    
    # Profile information
    full_name = db.Column(db.String(200))
    bio = db.Column(db.Text)
    followers = db.Column(db.Integer, default=0)
    
    # Contact information
    email = db.Column(db.String(200))
    website = db.Column(db.String(500))
    location = db.Column(db.String(200))
    profile_url = db.Column(db.String(500))

    # New fields for advanced scraping
    company_name = db.Column(db.String(200))
    company_industry = db.Column(db.String(200))
    company_size = db.Column(db.String(100)) # e.g., "1-10", "11-50", "51-200"
    job_title = db.Column(db.String(200))
    tech_stack = db.Column(db.Text) # Stored as JSON string of technologies

    # CRM Integration
    salesforce_id = db.Column(db.String(200), unique=True, nullable=True)
    hubspot_id = db.Column(db.String(200), unique=True, nullable=True)

    # Metrics
    engagement_score = db.Column(db.Float, default=0.0, index=True)
    
    # Tags (stored as JSON)
    tags = db.Column(db.Text, default='[]')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'username', 'platform', name='_user_username_platform_uc'),
    )
    
    def __repr__(self):
        return f'<Lead {self.username} on {self.platform}>'
    
    @property
    def tags_list(self):
        """Return tags as a Python list"""
        try:
            return json.loads(self.tags) if self.tags else []
        except:
            return []
    
    @tags_list.setter
    def tags_list(self, value):
        """Set tags from a Python list"""
        if isinstance(value, list):
            self.tags = json.dumps(value)
        elif isinstance(value, str):
            # Handle comma-separated string
            self.tags = json.dumps([tag.strip() for tag in value.split(',') if tag.strip()])
        else:
            self.tags = '[]'
    
    def to_dict(self):
        """Convert lead to dictionary for API responses"""
        return {
            'id': self.id,
            'username': self.username,
            'platform': self.platform,
            'full_name': self.full_name,
            'bio': self.bio,
            'followers': self.followers,
            'email': self.email,
            'website': self.website,
            'location': self.location,
            'profile_url': self.profile_url,
            'company_name': self.company_name,
            'company_industry': self.company_industry,
            'company_size': self.company_size,
            'job_title': self.job_title,
            'tech_stack': json.loads(self.tech_stack) if self.tech_stack else [],
            'engagement_score': self.engagement_score,
            'tags': self.tags_list,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    @staticmethod
    def calculate_engagement_score(followers, likes_avg=0, comments_avg=0):
        """Calculate engagement score (0-100)"""
        if followers == 0:
            return 0.0
        
        engagement_rate = ((likes_avg + comments_avg * 2) / followers) * 100
        score = min(100, engagement_rate * 10)
        follower_bonus = min(20, followers / 10000)
        
        return round(min(100, score + follower_bonus), 2)
    
    @staticmethod
    def search_leads(user_id, query=None, platform=None, min_followers=0, min_engagement=0.0,
                    tags=None, limit=100, offset=0, order_by='engagement_score'):
        """
        Advanced search with multiple filters
        Returns tuple: (leads, total_count)
        """
        # Base query
        q = Lead.query.filter_by(user_id=user_id)
        
        # Apply filters
        if query:
            search_term = f'%{query}%'
            q = q.filter(
                db.or_(
                    Lead.username.ilike(search_term),
                    Lead.full_name.ilike(search_term),
                    Lead.bio.ilike(search_term),
                    Lead.email.ilike(search_term)
                )
            )
        
        if platform and platform != 'all':
            q = q.filter(Lead.platform == platform)
        
        if min_followers > 0:
            q = q.filter(Lead.followers >= min_followers)
        
        if min_engagement > 0:
            q = q.filter(Lead.engagement_score >= min_engagement)
        
        if tags:
            # Search for tags in JSON field
            for tag in tags if isinstance(tags, list) else [tags]:
                q = q.filter(Lead.tags.contains(tag))
        
        # Get total count before pagination
        total_count = q.count()
        
        # Apply ordering
        order_column = getattr(Lead, order_by, Lead.engagement_score)
        q = q.order_by(order_column.desc())
        
        # Apply pagination
        leads = q.limit(limit).offset(offset).all()
        
        return leads, total_count
    
    @staticmethod
    def get_statistics(user_id):
        """Get database statistics"""
        stats = {
            'total_leads': Lead.query.filter_by(user_id=user_id).count(),
            'by_platform': {},
            'avg_followers': 0,
            'avg_engagement': 0,
            'total_followers': 0,
            'top_platforms': [],
            'recent_leads': []
        }
        
        # Platform distribution
        platform_stats = db.session.query(
            Lead.platform,
            db.func.count(Lead.id).label('count'),
            db.func.avg(Lead.followers).label('avg_followers'),
            db.func.avg(Lead.engagement_score).label('avg_engagement')
        ).filter_by(user_id=user_id).group_by(Lead.platform).all()
        
        for platform, count, avg_f, avg_e in platform_stats:
            stats['by_platform'][platform] = {
                'count': count,
                'avg_followers': round(avg_f or 0, 2),
                'avg_engagement': round(avg_e or 0, 2)
            }
        
        # Overall averages
        averages = db.session.query(
            db.func.avg(Lead.followers).label('avg_followers'),
            db.func.avg(Lead.engagement_score).label('avg_engagement'),
            db.func.sum(Lead.followers).label('total_followers')
        ).filter_by(user_id=user_id).first()
        
        if averages:
            stats['avg_followers'] = round(averages.avg_followers or 0, 2)
            stats['avg_engagement'] = round(averages.avg_engagement or 0, 2)
            stats['total_followers'] = averages.total_followers or 0
        
        # Top platforms by count
        stats['top_platforms'] = sorted(
            stats['by_platform'].items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:5]
        
        # Recent leads
        stats['recent_leads'] = Lead.query.filter_by(user_id=user_id).order_by(Lead.created_at.desc()).limit(5).all()
        
        return stats
    
    @staticmethod
    def get_top_performers(user_id, limit=10):
        """Get top performing leads by engagement score"""
        return Lead.query.filter_by(user_id=user_id).order_by(Lead.engagement_score.desc()).limit(limit).all()
    
    @staticmethod
    def get_all_tags(user_id):
        """Get all unique tags across all leads"""
        all_tags = set()
        leads = Lead.query.filter_by(user_id=user_id).all()
        
        for lead in leads:
            all_tags.update(lead.tags_list)
        
        return sorted(list(all_tags))


class LeadNote(db.Model):
    """Model for storing notes related to leads"""

    __tablename__ = 'lead_notes'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    note_type = db.Column(db.String(50), default='general') # e.g., 'general', 'call', 'meeting', 'email'
    is_important = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead = db.relationship('Lead', backref=db.backref('notes', lazy=True, cascade="all, delete-orphan"))
    author = db.relationship('User', backref=db.backref('lead_notes', lazy=True))

    def __repr__(self):
        return f'<LeadNote {self.id} for Lead {self.lead_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'user_id': self.user_id,
            'content': self.content,
            'note_type': self.note_type,
            'is_important': self.is_important,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }


class EmailLog(db.Model):
    """Model for logging sent emails"""

    __tablename__ = 'email_logs'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False) # e.g., 'sent', 'failed'
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    lead = db.relationship('Lead', backref=db.backref('email_logs', lazy=True))
    sender = db.relationship('User', backref=db.backref('sent_emails', lazy=True))

    def __repr__(self):
        return f'<EmailLog {self.id} to Lead {self.lead_id} - {self.subject}>'


class ChatMessage(db.Model):
    """Model for storing chat messages"""

    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'model'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lead = db.relationship('Lead', backref=db.backref('chat_messages', lazy=True, cascade="all, delete-orphan"))
    author = db.relationship('User', backref=db.backref('chat_messages', lazy=True))

    def __repr__(self):
        return f'<ChatMessage {self.id} from {self.role}>'

    def to_dict(self):
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'user_id': self.user_id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat()
        }


import uuid
import secrets

class APIKey(db.Model):
    """Model for storing API keys"""

    __tablename__ = 'api_keys'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    key = db.Column(db.String(255), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    user = db.relationship('User', backref=db.backref('api_keys', lazy=True))

    def __repr__(self):
        return f'<APIKey {self.id} for User {self.user_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'key': self.key,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active
        }

class LeadManager:
    """Manager class for lead operations"""
    
    @staticmethod
    def create_lead(data):
        """Create a new lead"""
        lead = Lead(
            user_id=data.get('user_id'),
            username=data.get('username'),
            platform=data.get('platform'),
            full_name=data.get('full_name'),
            bio=data.get('bio'),
            followers=data.get('followers', 0),
            email=data.get('email'),
            website=data.get('website'),
            location=data.get('location'),
            profile_url=data.get('profile_url'),
            company_name=data.get('company_name'),
            company_industry=data.get('company_industry'),
            company_size=data.get('company_size'),
            job_title=data.get('job_title'),
            tech_stack=data.get('tech_stack'),
            engagement_score=data.get('engagement_score', 0)
        )
        
        # Handle tags
        if 'tags' in data:
            lead.tags_list = data['tags']

        # Handle tech_stack
        if 'tech_stack' in data and isinstance(data['tech_stack'], list):
            lead.tech_stack = json.dumps(data['tech_stack'])
        
        db.session.add(lead)
        db.session.commit()
        
        return lead
    
    @staticmethod
    def update_lead(lead_id, data):
        """Update an existing lead"""
        lead = Lead.query.get(lead_id)
        if not lead:
            return None
        
        # Update fields
        for key, value in data.items():
            if key == 'tags':
                lead.tags_list = value
            elif key == 'tech_stack' and isinstance(value, list):
                lead.tech_stack = json.dumps(value)
            elif hasattr(lead, key) and key not in ['id', 'created_at']:
                setattr(lead, key, value)
        
        lead.last_updated = datetime.utcnow()
        db.session.commit()
        
        return lead
    
    @staticmethod
    def delete_lead(lead_id):
        """Delete a lead"""
        lead = Lead.query.get(lead_id)
        if not lead:
            return False
        
        db.session.delete(lead)
        db.session.commit()
        
        return True
    
    @staticmethod
    def bulk_delete(lead_ids):
        """Delete multiple leads"""
        count = Lead.query.filter(Lead.id.in_(lead_ids)).delete(synchronize_session=False)
        db.session.commit()
        return count
    
    @staticmethod
    def bulk_update_tags(lead_ids, tags, action='add'):
        """
        Bulk update tags for multiple leads
        action: 'add', 'remove', or 'replace'
        """
        leads = Lead.query.filter(Lead.id.in_(lead_ids)).all()
        
        for lead in leads:
            current_tags = lead.tags_list
            
            if action == 'add':
                new_tags = list(set(current_tags + tags))
            elif action == 'remove':
                new_tags = [tag for tag in current_tags if tag not in tags]
            else:  # replace
                new_tags = tags
            
            lead.tags_list = new_tags
            lead.last_updated = datetime.utcnow()
        
        db.session.commit()
        return len(leads)
    
    @staticmethod
    def import_leads(leads_data, user_id):
        """
        Bulk import leads from list of dictionaries
        Returns: (success_count, error_count, errors_list)
        """
        success_count = 0
        error_count = 0
        errors = []

        for idx, data in enumerate(leads_data):
            try:
                # Associate lead with the current user
                data['user_id'] = user_id

                # Check if lead already exists for this user
                existing = Lead.query.filter_by(
                    user_id=user_id,
                    username=data.get('username'),
                    platform=data.get('platform')
                ).first()

                if existing:
                    errors.append(f"Row {idx + 1}: Lead already exists for this user - {data.get('username')}")
                    error_count += 1
                    continue

                LeadManager.create_lead(data)
                success_count += 1

            except Exception as e:
                db.session.rollback()
                errors.append(f"Row {idx + 1}: {str(e)}")
                error_count += 1
        
        return success_count, error_count, errors