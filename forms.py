# forms.py - WTForms for form validation

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, FloatField, SelectField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, Optional, URL, NumberRange, Length, ValidationError, EqualTo
from models import Lead

class LeadForm(FlaskForm):
    """Form for adding/editing leads"""
    
    username = StringField('Username', 
        validators=[
            DataRequired(message='Username is required'),
            Length(min=2, max=100, message='Username must be between 2 and 100 characters')
        ],
        render_kw={"placeholder": "e.g., @johndoe"}
    )
    
    platform = SelectField('Platform',
        choices=[
            ('', 'Select Platform'),
            ('instagram', 'Instagram'),
            ('twitter', 'Twitter'),
            ('linkedin', 'LinkedIn'),
            ('facebook', 'Facebook'),
            ('tiktok', 'TikTok'),
            ('youtube', 'YouTube'),
            ('pinterest', 'Pinterest'),
            ('snapchat', 'Snapchat'),
            ('other', 'Other')
        ],
        validators=[DataRequired(message='Platform is required')]
    )
    
    full_name = StringField('Full Name',
        validators=[
            Optional(),
            Length(max=200, message='Full name cannot exceed 200 characters')
        ],
        render_kw={"placeholder": "John Doe"}
    )
    
    bio = TextAreaField('Bio',
        validators=[Optional()],
        render_kw={"placeholder": "Brief description about the lead...", "rows": 4}
    )
    
    followers = IntegerField('Followers',
        validators=[
            Optional(),
            NumberRange(min=0, max=1000000000, message='Followers must be between 0 and 1 billion')
        ],
        default=0,
        render_kw={"placeholder": "0"}
    )
    
    email = StringField('Email',
        validators=[
            Optional(),
            Email(message='Invalid email address'),
            Length(max=200, message='Email cannot exceed 200 characters')
        ],
        render_kw={"placeholder": "email@example.com"}
    )
    
    website = StringField('Website',
        validators=[
            Optional(),
            URL(message='Invalid URL format'),
            Length(max=500, message='Website URL cannot exceed 500 characters')
        ],
        render_kw={"placeholder": "https://example.com"}
    )
    
    location = StringField('Location',
        validators=[
            Optional(),
            Length(max=200, message='Location cannot exceed 200 characters')
        ],
        render_kw={"placeholder": "New York, USA"}
    )
    
    profile_url = StringField('Profile URL',
        validators=[
            Optional(),
            URL(message='Invalid URL format'),
            Length(max=500, message='Profile URL cannot exceed 500 characters')
        ],
        render_kw={"placeholder": "https://instagram.com/username"}
    )
    
    engagement_score = FloatField('Engagement Score',
        validators=[
            Optional(),
            NumberRange(min=0, max=100, message='Engagement score must be between 0 and 100')
        ],
        default=0.0,
        render_kw={"placeholder": "0.0", "step": "0.01"}
    )
    
    tags = StringField('Tags',
        validators=[Optional()],
        render_kw={"placeholder": "influencer, tech, marketing (comma-separated)"}
    )
    
    def validate_username(self, field):
        """Custom validation: Check for duplicate username on same platform"""
        # Only check during creation (when no lead_id is set)
        if not hasattr(self, 'lead_id') or self.lead_id is None:
            existing_lead = Lead.query.filter_by(
                username=field.data,
                platform=self.platform.data
            ).first()
            
            if existing_lead:
                raise ValidationError(
                    f'A lead with username "{field.data}" already exists on {self.platform.data}'
                )
    
    def set_lead_id(self, lead_id):
        """Set lead_id for edit mode (to skip duplicate validation)"""
        self.lead_id = lead_id


class SearchForm(FlaskForm):
    """Form for searching and filtering leads"""
    
    search = StringField('Search',
        validators=[Optional()],
        render_kw={"placeholder": "Search username, name, or bio..."}
    )
    
    platform = SelectField('Platform',
        choices=[
            ('all', 'All Platforms'),
            ('instagram', 'Instagram'),
            ('twitter', 'Twitter'),
            ('linkedin', 'LinkedIn'),
            ('facebook', 'Facebook'),
            ('tiktok', 'TikTok'),
            ('youtube', 'YouTube'),
            ('pinterest', 'Pinterest'),
            ('snapchat', 'Snapchat'),
            ('other', 'Other')
        ],
        default='all'
    )
    
    min_followers = IntegerField('Min Followers',
        validators=[
            Optional(),
            NumberRange(min=0, message='Minimum followers cannot be negative')
        ],
        default=0
    )
    
    min_engagement = FloatField('Min Engagement Score',
        validators=[
            Optional(),
            NumberRange(min=0, max=100, message='Engagement score must be between 0 and 100')
        ],
        default=0.0
    )
    
    sort_by = SelectField('Sort By',
        choices=[
            ('engagement_score', 'Engagement Score'),
            ('followers', 'Followers'),
            ('created_at', 'Date Added'),
            ('last_updated', 'Last Updated'),
            ('username', 'Username')
        ],
        default='engagement_score'
    )


class BulkActionForm(FlaskForm):
    """Form for bulk operations"""
    
    action = SelectField('Action',
        choices=[
            ('', 'Select Action'),
            ('delete', 'Delete Selected'),
            ('add_tags', 'Add Tags'),
            ('remove_tags', 'Remove Tags'),
            ('export', 'Export Selected')
        ],
        validators=[DataRequired(message='Please select an action')]
    )
    
    tags = StringField('Tags',
        validators=[Optional()],
        render_kw={"placeholder": "tag1, tag2, tag3"}
    )


class ImportForm(FlaskForm):
    """Form for importing leads from file"""
    
    duplicate_action = SelectField('Handle Duplicates',
        choices=[
            ('skip', 'Skip Duplicates'),
            ('update', 'Update Existing'),
            ('create_new', 'Create New Entry')
        ],
        default='skip',
        validators=[DataRequired()]
    )


class EngagementCalculatorForm(FlaskForm):
    """Form for calculating engagement scores"""
    
    followers = IntegerField('Followers',
        validators=[
            DataRequired(message='Followers count is required'),
            NumberRange(min=1, message='Followers must be at least 1')
        ],
        render_kw={"placeholder": "10000"}
    )
    
    avg_likes = IntegerField('Average Likes per Post',
        validators=[
            Optional(),
            NumberRange(min=0, message='Average likes cannot be negative')
        ],
        default=0,
        render_kw={"placeholder": "500"}
    )
    
    avg_comments = IntegerField('Average Comments per Post',
        validators=[
            Optional(),
            NumberRange(min=0, message='Average comments cannot be negative')
        ],
        default=0,
        render_kw={"placeholder": "50"}
    )


from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, FloatField, SelectField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, URL, NumberRange, Length, ValidationError, EqualTo
from models import Lead, User # Import User here

class LeadForm(FlaskForm):
    """Form for adding/editing leads"""
    
    username = StringField('Username',
        validators=[
            DataRequired(message='Username is required'),
            Length(min=2, max=100, message='Username must be between 2 and 100 characters')
        ],
        render_kw={"placeholder": "e.g., @johndoe"}
    )
    
    platform = SelectField('Platform',
        choices=[
            ('', 'Select Platform'),
            ('instagram', 'Instagram'),
            ('twitter', 'Twitter'),
            ('linkedin', 'LinkedIn'),
            ('facebook', 'Facebook'),
            ('tiktok', 'TikTok'),
            ('youtube', 'YouTube'),
            ('pinterest', 'Pinterest'),
            ('snapchat', 'Snapchat'),
            ('other', 'Other')
        ],
        validators=[DataRequired(message='Platform is required')]
    )
    
    full_name = StringField('Full Name',
        validators=[
            Optional(),
            Length(max=200, message='Full name cannot exceed 200 characters')
        ],
        render_kw={"placeholder": "John Doe"}
    )
    
    bio = TextAreaField('Bio',
        validators=[Optional()],
        render_kw={"placeholder": "Brief description about the lead...", "rows": 4}
    )
    
    followers = IntegerField('Followers',
        validators=[
            Optional(),
            NumberRange(min=0, max=1000000000, message='Followers must be between 0 and 1 billion')
        ],
        default=0,
        render_kw={"placeholder": "0"}
    )
    
    email = StringField('Email',
        validators=[
            Optional(),
            Email(message='Invalid email address'),
            Length(max=200, message='Email cannot exceed 200 characters')
        ],
        render_kw={"placeholder": "email@example.com"}
    )
    
    website = StringField('Website',
        validators=[
            Optional(),
            URL(message='Invalid URL format'),
            Length(max=500, message='Website URL cannot exceed 500 characters')
        ],
        render_kw={"placeholder": "https://example.com"}
    )
    
    location = StringField('Location',
        validators=[
            Optional(),
            Length(max=200, message='Location cannot exceed 200 characters')
        ],
        render_kw={"placeholder": "New York, USA"}
    )
    
    profile_url = StringField('Profile URL',
        validators=[
            Optional(),
            URL(message='Invalid URL format'),
            Length(max=500, message='Profile URL cannot exceed 500 characters')
        ],
        render_kw={"placeholder": "https://instagram.com/username"}
    )
    
    engagement_score = FloatField('Engagement Score',
        validators=[
            Optional(),
            NumberRange(min=0, max=100, message='Engagement score must be between 0 and 100')
        ],
        default=0.0,
        render_kw={"placeholder": "0.0", "step": "0.01"}
    )
    
    tags = StringField('Tags',
        validators=[Optional()],
        render_kw={"placeholder": "influencer, tech, marketing (comma-separated)"}
    )
    
    def validate_username(self, field):
        """Custom validation: Check for duplicate username on same platform"""
        # Only check during creation (when no lead_id is set)
        if not hasattr(self, 'lead_id') or self.lead_id is None:
            existing_lead = Lead.query.filter_by(
                username=field.data,
                platform=self.platform.data
            ).first()
            
            if existing_lead:
                raise ValidationError(
                    f'A lead with username "{field.data}" already exists on {self.platform.data}'
                )
    
    def set_lead_id(self, lead_id):
        """Set lead_id for edit mode (to skip duplicate validation)"""
        self.lead_id = lead_id


class SearchForm(FlaskForm):
    """Form for searching and filtering leads"""
    
    search = StringField('Search',
        validators=[Optional()],
        render_kw={"placeholder": "Search username, name, or bio..."}
    )
    
    platform = SelectField('Platform',
        choices=[
            ('all', 'All Platforms'),
            ('instagram', 'Instagram'),
            ('twitter', 'Twitter'),
            ('linkedin', 'LinkedIn'),
            ('facebook', 'Facebook'),
            ('tiktok', 'TikTok'),
            ('youtube', 'YouTube'),
            ('pinterest', 'Pinterest'),
            ('snapchat', 'Snapchat'),
            ('other', 'Other')
        ],
        default='all'
    )
    
    min_followers = IntegerField('Min Followers',
        validators=[
            Optional(),
            NumberRange(min=0, message='Minimum followers cannot be negative')
        ],
        default=0
    )
    
    min_engagement = FloatField('Min Engagement Score',
        validators=[
            Optional(),
            NumberRange(min=0, max=100, message='Engagement score must be between 0 and 100')
        ],
        default=0.0
    )
    
    sort_by = SelectField('Sort By',
        choices=[
            ('engagement_score', 'Engagement Score'),
            ('followers', 'Followers'),
            ('created_at', 'Date Added'),
            ('last_updated', 'Last Updated'),
            ('username', 'Username')
        ],
        default='engagement_score'
    )


class BulkActionForm(FlaskForm):
    """Form for bulk operations"""
    
    action = SelectField('Action',
        choices=[
            ('', 'Select Action'),
            ('delete', 'Delete Selected'),
            ('add_tags', 'Add Tags'),
            ('remove_tags', 'Remove Tags'),
            ('export', 'Export Selected')
        ],
        validators=[DataRequired(message='Please select an action')]
    )
    
    tags = StringField('Tags',
        validators=[Optional()],
        render_kw={"placeholder": "tag1, tag2, tag3"}
    )


class ImportForm(FlaskForm):
    """Form for importing leads from file"""
    
    duplicate_action = SelectField('Handle Duplicates',
        choices=[
            ('skip', 'Skip Duplicates'),
            ('update', 'Update Existing'),
            ('create_new', 'Create New Entry')
        ],
        default='skip',
        validators=[DataRequired()]
    )


class EngagementCalculatorForm(FlaskForm):
    """Form for calculating engagement scores"""
    
    followers = IntegerField('Followers',
        validators=[
            DataRequired(message='Followers count is required'),
            NumberRange(min=1, message='Followers must be at least 1')
        ],
        render_kw={"placeholder": "10000"}
    )
    
    avg_likes = IntegerField('Average Likes per Post',
        validators=[
            Optional(),
            NumberRange(min=0, message='Average likes cannot be negative')
        ],
        default=0,
        render_kw={"placeholder": "500"}
    )
    
    avg_comments = IntegerField('Average Comments per Post',
        validators=[
            Optional(),
            NumberRange(min=0, message='Average comments cannot be negative')
        ],
        default=0,
        render_kw={"placeholder": "50"}
    )


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Confirm Password',
                             validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

class LoginForm(FlaskForm):
    """Form for user login"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')

class ProfileForm(FlaskForm):
    """Form for updating user profile"""
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])

class NoteForm(FlaskForm):
    """Form for adding notes to leads"""
    content = TextAreaField('Note Content', validators=[DataRequired(), Length(min=1, max=500)])
    note_type = SelectField('Note Type',
        choices=[
            ('general', 'General'),
            ('call', 'Call'),
            ('meeting', 'Meeting'),
            ('email', 'Email')
        ],
        default='general',
        validators=[DataRequired()]
    )
    is_important = BooleanField('Important')

class GeminiLeadGenerationForm(FlaskForm):
    """Form for generating leads using Google Gemini API"""
    prompt = TextAreaField('Lead Generation Prompt',
        validators=[DataRequired(), Length(min=10, max=1000)],
        render_kw={"placeholder": "e.g., 'influencers in tech in Silicon Valley with over 10k followers'", "rows": 5}
    )
    submit = SubmitField('Generate Leads')

class UserSearchForm(FlaskForm):
    """Form for searching users"""
    search = StringField('Search', validators=[Optional()], render_kw={"placeholder": "Search username or email..."})

class ScrapeLeadsForm(FlaskForm):
    """Form for web scraping leads from a URL"""
    url = StringField('URL to Scrape',
        validators=[DataRequired(message='URL is required')],
        render_kw={"placeholder": "e.g., https://example.com/leads-page or www.example.com"}
    )
    submit = SubmitField('Scrape Leads')

class GeminiLeadGenerationForm(FlaskForm):
    """Form for generating leads using Google Gemini API"""
    prompt = TextAreaField('Lead Generation Prompt',
        validators=[DataRequired(), Length(min=10, max=1000)],
        render_kw={"placeholder": "e.g., 'influencers in tech in Silicon Valley with over 10k followers'", "rows": 5}
    )
    submit = SubmitField('Generate Leads')