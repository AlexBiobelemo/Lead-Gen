# app.py - Main Flask application

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session, stream_with_context
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from flask_mail import Mail, Message
import json
import re
import traceback # Import traceback for detailed error logging
from simple_salesforce import Salesforce
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput
import tweepy
from instagrapi import Client
import google.generativeai as genai
from config import config
from models import db, Lead, LeadManager, User, LeadNote, EmailLog, ChatMessage, APIKey
from forms import LeadForm, SearchForm, BulkActionForm, ImportForm, EngagementCalculatorForm, RegistrationForm, LoginForm, ProfileForm, NoteForm, UserSearchForm, GeminiLeadGenerationForm, ScrapeLeadsForm
from utils import (
    export_leads_to_csv, export_leads_to_json, parse_csv_file, parse_json_file,
    create_response, require_api_key, require_rate_limit, allowed_file,
    format_number, format_percentage, format_relative_time
)
import os
from datetime import datetime, timedelta
import io
from scraper import scrape_leads
import markdown # Import the markdown library
import secrets

# Create Flask app
def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    # Initialize Flask-Bootstrap
    Bootstrap(app)
    
    # Initialize Flask-Mail
    mail = Mail(app)
    app.mail = mail # Attach mail to app for easy access
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    # Configure Google Gemini API
    if app.config.get('GOOGLE_GEMINI_API_KEY'):
        genai.configure(api_key=app.config['GOOGLE_GEMINI_API_KEY'])
    else:
        print("WARNING: GOOGLE_GEMINI_API_KEY is not set in config.")

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    # Register Jinja filters
    app.jinja_env.filters['format_number'] = format_number
    app.jinja_env.filters['format_percentage'] = format_percentage
    app.jinja_env.filters['format_relative_time'] = format_relative_time
    # Register the markdown filter
    app.jinja_env.filters['markdown'] = lambda text: markdown.markdown(text)
    
    # Register Jinja globals (functions)
    app.jinja_env.globals['max'] = max
    app.jinja_env.globals['min'] = min
    
    # Register min as a filter (optional, if still needed for specific cases)
    app.jinja_env.filters['min_val'] = min
    
    return app

app = create_app(os.getenv('FLASK_ENV', 'development'))


# ============================================================================
# User Authentication Routes
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user"""
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, member_since=datetime.utcnow())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Log in a user"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember.data)
        return redirect(url_for('dashboard'))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    """Log out a user"""
    logout_user()
    return redirect(url_for('dashboard'))

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html', title='Profile')

@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    form = ProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your changes have been saved.', 'success')
        return redirect(url_for('profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('edit_profile.html', title='Edit Profile', form=form)

# ============================================================================
# Web Routes
# ============================================================================

@app.route('/users')
@login_required
def users_list():
    """List all users with search functionality"""
    form = UserSearchForm(request.args)
    query = User.query

    if form.validate():
        if form.search.data:
            search_term = f"%{form.search.data}%"
            query = query.filter(
                (User.username.ilike(search_term)) |
                (User.email.ilike(search_term))
            )
    
    users = query.all()
    return render_template('users_list.html', users=users, form=form)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with lead listing and filters"""
    # Get filter parameters
    search_query = request.args.get('search', '')
    platform = request.args.get('platform', 'all')
    min_followers = int(request.args.get('min_followers', 0))
    min_engagement = float(request.args.get('min_engagement', 0.0))
    sort_by = request.args.get('sort_by', 'engagement_score')
    page = int(request.args.get('page', 1))
    
    # Search leads
    leads, total = Lead.search_leads(
        user_id=current_user.id,
        query=search_query,
        platform=platform,
        min_followers=min_followers,
        min_engagement=min_engagement,
        limit=app.config['LEADS_PER_PAGE'],
        offset=(page - 1) * app.config['LEADS_PER_PAGE'],
        order_by=sort_by
    )
    
    # Get statistics
    stats = Lead.get_statistics(current_user.id)
    
    # Pagination info
    total_pages = (total + app.config['LEADS_PER_PAGE'] - 1) // app.config['LEADS_PER_PAGE']
    
    # Create form for filters
    search_form = SearchForm(
        search=search_query,
        platform=platform,
        min_followers=min_followers,
        min_engagement=min_engagement,
        sort_by=sort_by
    )
    
    if request.args.get('ajax'):
        leads_data = [lead.to_dict() for lead in leads]
        has_more = (page * app.config['LEADS_PER_PAGE']) < total
        return jsonify(leads=leads_data, has_more=has_more)

    return render_template('dashboard.html',
                         leads=leads,
                         stats=stats,
                         search_form=search_form,
                         page=page,
                         total_pages=total_pages,
                         total=total)


@app.route('/add-lead', methods=['GET', 'POST'])
@login_required
def add_lead():
    """Add new lead"""
    form = LeadForm()
    
    if form.validate_on_submit():
        try:
            # Create lead data
            lead_data = {
                'user_id': current_user.id,
                'username': form.username.data,
                'platform': form.platform.data,
                'full_name': form.full_name.data,
                'bio': form.bio.data,
                'followers': form.followers.data or 0,
                'email': form.email.data,
                'website': form.website.data,
                'location': form.location.data,
                'profile_url': form.profile_url.data,
                'engagement_score': form.engagement_score.data or 0.0,
                'tags': form.tags.data
            }
            
            # Create lead
            lead = LeadManager.create_lead(lead_data)
            
            flash(f'Lead "{lead.username}" added successfully!', 'success')
            return redirect(url_for('view_lead', lead_id=lead.id))
            
        except Exception as e:
            flash(f'Error adding lead: {str(e)}', 'error')
    
    return render_template('add_lead.html', form=form)


@app.route('/view-lead/<int:lead_id>')
@login_required
def view_lead(lead_id):
    """View lead details"""
    lead = Lead.query.get_or_404(lead_id)
    form = NoteForm()  # Instantiate NoteForm here
    notes = LeadNote.query.filter_by(lead_id=lead.id).order_by(LeadNote.created_at.desc()).all() # Get all notes for a lead, ordered by creation date
    return render_template('view_lead.html', lead=lead, notes=notes, form=form)


@app.route('/lead/<int:lead_id>/add-note', methods=['GET', 'POST'])
@login_required
def add_note(lead_id):
    """Add a new note to a lead"""
    lead = Lead.query.get_or_404(lead_id)
    form = NoteForm()
    if form.validate_on_submit():
        note = LeadNote(
            lead_id=lead.id,
            user_id=current_user.id,
            content=form.content.data,
            note_type=form.note_type.data,
            is_important=form.is_important.data
        )
        db.session.add(note)
        db.session.commit()
        flash('Note added successfully!', 'success')
        return redirect(url_for('view_lead', lead_id=lead.id))
    return render_template('add_note.html', form=form, lead=lead)


@app.route('/lead/<int:lead_id>/delete-note/<int:note_id>', methods=['POST'])
@login_required
def delete_note(lead_id, note_id):
    """Delete a note from a lead"""
    note = LeadNote.query.get_or_404(note_id)
    if note.lead_id != lead_id or note.user_id != current_user.id:
        flash('You do not have permission to delete this note.', 'error')
        return redirect(url_for('view_lead', lead_id=lead_id))
    
    db.session.delete(note)
    db.session.commit()
    flash('Note deleted successfully!', 'success')
    return redirect(url_for('view_lead', lead_id=lead_id))


@app.route('/edit-lead/<int:lead_id>', methods=['GET', 'POST'])
@login_required
def edit_lead(lead_id):
    """Edit existing lead"""
    lead = Lead.query.get_or_404(lead_id)
    form = LeadForm(obj=lead)
    form.set_lead_id(lead_id)  # Set ID to skip duplicate validation
    
    if form.validate_on_submit():
        try:
            # Update lead data
            update_data = {
                'username': form.username.data,
                'platform': form.platform.data,
                'full_name': form.full_name.data,
                'bio': form.bio.data,
                'followers': form.followers.data or 0,
                'email': form.email.data,
                'website': form.website.data,
                'location': form.location.data,
                'profile_url': form.profile_url.data,
                'engagement_score': form.engagement_score.data or 0.0,
                'tags': form.tags.data
            }
            
            # Update lead
            LeadManager.update_lead(lead_id, update_data)
            
            flash(f'Lead "{lead.username}" updated successfully!', 'success')
            return redirect(url_for('view_lead', lead_id=lead_id))
            
        except Exception as e:
            flash(f'Error updating lead: {str(e)}', 'error')
    else:
        # Pre-fill tags field
        if request.method == 'GET':
            form.tags.data = ', '.join(lead.tags_list)
    
    return render_template('edit_lead.html', form=form, lead=lead)


@app.route('/delete-lead/<int:lead_id>', methods=['POST'])
@login_required
def delete_lead(lead_id):
    """Delete a lead"""
    lead = Lead.query.get_or_404(lead_id)
    username = lead.username
    
    try:
        LeadManager.delete_lead(lead_id)
        flash(f'Lead "{username}" deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting lead: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))


@app.route('/export')
@login_required
def export_leads():
    """Export leads to CSV"""
    # Get filter parameters (same as dashboard)
    search_query = request.args.get('search', '')
    platform = request.args.get('platform', 'all')
    min_followers = int(request.args.get('min_followers', 0))
    min_engagement = float(request.args.get('min_engagement', 0.0))
    
    # Get all matching leads (no limit)
    leads, _ = Lead.search_leads(
        user_id=current_user.id,
        query=search_query,
        platform=platform,
        min_followers=min_followers,
        min_engagement=min_engagement,
        limit=10000  # High limit for export
    )
    
    # Generate CSV
    csv_data = export_leads_to_csv(leads)
    
    # Create filename with timestamp
    filename = f'leads_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    # Send file
    return send_file(
        io.BytesIO(csv_data.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@app.route('/import-leads', methods=['GET', 'POST'])
@login_required
def import_leads():
    """Import leads from CSV/JSON file"""
    form = ImportForm()
    
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename, app.config['ALLOWED_EXTENSIONS']):
            try:
                # Read file content
                file_content = file.read()
                
                # Parse based on file type
                if file.filename.endswith('.csv'):
                    leads_data = parse_csv_file(file_content)
                elif file.filename.endswith('.json'):
                    leads_data = parse_json_file(file_content)
                else:
                    flash('Unsupported file format', 'error')
                    return redirect(request.url)
                
                # Import leads
                success_count, error_count, errors = LeadManager.import_leads(leads_data, current_user.id)
                
                # Show results
                flash(f'Import completed: {success_count} leads added, {error_count} errors', 
                      'success' if error_count == 0 else 'warning')
                
                if errors:
                    for error in errors[:10]:  # Show first 10 errors
                        flash(error, 'error')
                
                return redirect(url_for('dashboard'))
                
            except Exception as e:
                flash(f'Error importing file: {str(e)}', 'error')
        else:
            flash('Invalid file type. Please upload CSV or JSON file.', 'error')
    
    return render_template('import_leads.html', form=form)


@app.route('/analytics')
@login_required
def analytics():
    """Analytics dashboard"""
    stats = Lead.get_statistics(current_user.id)
    top_performers = Lead.get_top_performers(current_user.id, limit=10)
    all_tags = Lead.get_all_tags(current_user.id)
    
    return render_template('analytics.html',
                         stats=stats,
                         top_performers=top_performers,
                         all_tags=all_tags)


@app.route('/bulk-actions', methods=['POST'])
@login_required
def bulk_actions():
    """Handle bulk operations on selected leads"""
    form = BulkActionForm()
    
    if form.validate_on_submit():
        action = form.action.data
        lead_ids = request.form.getlist('lead_ids[]')
        
        if not lead_ids:
            flash('No leads selected', 'error')
            return redirect(url_for('dashboard'))
        
        lead_ids = [int(lid) for lid in lead_ids]
        
        try:
            if action == 'delete':
                count = LeadManager.bulk_delete(lead_ids)
                flash(f'{count} leads deleted successfully', 'success')
                
            elif action == 'add_tags':
                tags = [tag.strip() for tag in form.tags.data.split(',') if tag.strip()]
                count = LeadManager.bulk_update_tags(lead_ids, tags, 'add')
                flash(f'Tags added to {count} leads', 'success')
                
            elif action == 'remove_tags':
                tags = [tag.strip() for tag in form.tags.data.split(',') if tag.strip()]
                count = LeadManager.bulk_update_tags(lead_ids, tags, 'remove')
                flash(f'Tags removed from {count} leads', 'success')
                
            elif action == 'export':
                leads = Lead.query.filter(Lead.id.in_(lead_ids)).all()
                csv_data = export_leads_to_csv(leads)
                filename = f'leads_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                
                return send_file(
                    io.BytesIO(csv_data.getvalue().encode('utf-8')),
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name=filename
                )
        
        except Exception as e:
            flash(f'Error performing bulk action: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))


@app.route('/calculate-engagement', methods=['GET', 'POST'])
@login_required
def calculate_engagement():
    """Tool to calculate engagement score"""
    form = EngagementCalculatorForm()
    result = None
    
    if form.validate_on_submit():
        score = Lead.calculate_engagement_score(
            form.followers.data,
            form.avg_likes.data or 0,
            form.avg_comments.data or 0
        )
        result = {
            'score': score,
            'followers': form.followers.data,
            'avg_likes': form.avg_likes.data or 0,
            'avg_comments': form.avg_comments.data or 0
        }
    
    return render_template('calculate_engagement.html', form=form, result=result)

@app.route('/generate-ai-leads', methods=['GET', 'POST'])
@login_required
def generate_ai_leads():
    """Generate leads using Google Gemini API"""
    form = GeminiLeadGenerationForm()
    generated_leads = []

    if form.validate_on_submit():
        prompt = form.prompt.data
        generated_leads = generate_leads_with_gemini(prompt)
        if generated_leads:
            flash(f'{len(generated_leads)} leads generated successfully!', 'success')
            session['generated_leads'] = generated_leads  # Store as list of dicts
        else:
            flash('No leads were generated. Please try a different prompt.', 'warning')
        
    # Retrieve generated leads from session if available for display
    if 'generated_leads' in session:
        generated_leads = session.get('generated_leads', [])

    return render_template('generate_ai_leads.html', form=form, generated_leads=generated_leads)


@app.route('/add-lead-from-ai', methods=['POST'])
@login_required
def add_lead_from_ai():
    """Add a single AI-generated lead to the database."""
    try:
        lead_data = {
            'user_id': current_user.id,
            'username': request.form.get('username'),
            'platform': request.form.get('platform'),
            'full_name': request.form.get('full_name'),
            'bio': request.form.get('bio'),
            'followers': int(request.form.get('followers', 0)),
            'email': request.form.get('email'),
            'website': request.form.get('website'),
            'location': request.form.get('location'),
            'profile_url': request.form.get('profile_url'),
            'engagement_score': float(request.form.get('engagement_score', 0.0)),
            'tags': request.form.get('tags'),
            'company_name': request.form.get('company_name'),
            'company_industry': request.form.get('company_industry'),
            'company_size': request.form.get('company_size'),
            'job_title': request.form.get('job_title'),
            'tech_stack': request.form.get('tech_stack')
        }

        # Basic validation for required fields
        if not lead_data.get('username') or not lead_data.get('platform'):
            flash("Skipping lead due to missing username or platform.", "error")
            return redirect(url_for('generate_ai_leads'))

        # Check for duplicates before adding
        existing_lead = Lead.query.filter_by(
            username=lead_data.get('username'),
            platform=lead_data.get('platform'),
            user_id=current_user.id
        ).first()

        if not existing_lead:
            LeadManager.create_lead(lead_data)
            flash(f"Lead '{lead_data.get('username')}' added successfully!", "success")
        else:
            flash(f"Lead '{lead_data.get('username')}' on {lead_data.get('platform')} already exists.", "info")

    except Exception as e:
        flash(f"Error adding lead: {str(e)}", "error")
    
    return redirect(url_for('generate_ai_leads'))


@app.route('/scrape-leads', methods=['GET', 'POST'])
@login_required
def scrape_leads_route():
    """Web scrape leads from a given URL"""
    form = ScrapeLeadsForm()
    scraped_leads = []

    if form.validate_on_submit():
        url = form.url.data
        scraped_data = scrape_leads(url)
        
        if scraped_data:
            flash(f'{len(scraped_data)} potential leads scraped from {url}!', 'success')
            session['scraped_leads'] = scraped_data
        else:
            flash(f'No leads were scraped from {url}. Please check the URL or try a different one.', 'warning')
    
    if 'scraped_leads' in session:
        scraped_leads = session.get('scraped_leads', [])

    return render_template('scrape_leads.html', form=form, scraped_leads=scraped_leads, csrf_token=form.csrf_token)


@app.route('/add-scraped-leads', methods=['POST'])
@login_required
def add_scraped_leads():
    """Add selected scraped leads to the database"""
    selected_indices = request.form.getlist('selected_leads')
    
    if not selected_indices:
        flash('No leads selected for addition.', 'warning')
        return redirect(url_for('scrape_leads_route'))

    scraped_leads_data = session.get('scraped_leads', [])
    
    added_count = 0
    for index_str in selected_indices:
        try:
            index = int(index_str)
            if 0 <= index < len(scraped_leads_data):
                lead_data = scraped_leads_data[index]
                # Ensure user_id is set for the current user
                lead_data['user_id'] = current_user.id
                # Basic validation for required fields
                if not lead_data.get('username') or not lead_data.get('platform'):
                    flash(f"Skipping lead due to missing username or platform: {lead_data}", "error")
                    continue

                # Check for duplicates before adding
                existing_lead = Lead.query.filter_by(
                    username=lead_data.get('username'),
                    platform=lead_data.get('platform'),
                    user_id=current_user.id
                ).first()

                if not existing_lead:
                    LeadManager.create_lead(lead_data)
                    added_count += 1
                else:
                    flash(f"Lead '{lead_data.get('username')}' on {lead_data.get('platform')} already exists.", "info")
            else:
                flash(f"Invalid lead index: {index_str}", "error")
        except Exception as e:
            flash(f"Error adding lead with index {index_str}: {str(e)}", "error")
            continue
    
    if added_count > 0:
        flash(f'{added_count} selected leads added to the database successfully!', 'success')
        session.pop('scraped_leads', None) # Clear scraped leads from session
    else:
        flash('No leads were added to the database.', 'warning')
        
    return redirect(url_for('dashboard'))



@app.route('/ai-chat/<int:lead_id>', methods=['GET', 'POST'])
@login_required
def ai_chat(lead_id):
    """AI Chat feature for a specific lead"""
    lead = Lead.query.get_or_404(lead_id)
    
    # Retrieve chat history from the database
    chat_history = ChatMessage.query.filter_by(lead_id=lead_id, user_id=current_user.id).order_by(ChatMessage.created_at).all()

    if request.method == 'POST':
        user_message = request.form.get('message')
        if user_message:
            # Save user message to the database
            new_user_message = ChatMessage(
                lead_id=lead_id,
                user_id=current_user.id,
                role='user',
                content=user_message
            )
            db.session.add(new_user_message)
            db.session.commit()
            
            try:
                model = genai.GenerativeModel('gemini-2.5-flash')
                # Construct a prompt that includes lead info and chat history
                full_chat_prompt = f"You are an AI assistant helping with lead management for {lead.full_name or lead.username} ({lead.platform}). Here's their info: Bio: {lead.bio or 'N/A'}, Followers: {lead.followers or 0}, Email: {lead.email or 'N/A'}, Location: {lead.location or 'N/A'}, Tags: {', '.join(lead.tags_list)}. \n\nPrevious conversation:\n"
                for msg in chat_history:
                    full_chat_prompt += f"{msg.role}: {msg.content}\n"
                full_chat_prompt += f"user: {user_message}\nAI:"

                response_stream = model.generate_content(full_chat_prompt, stream=True)
                
                # Stream the content directly to the client
                def generate_stream():
                    full_ai_response = ""
                    for chunk in response_stream:
                        text_chunk = chunk.text
                        full_ai_response += text_chunk
                        yield text_chunk
                    
                    # After streaming, save the full AI response to the database
                    new_ai_message = ChatMessage(
                        lead_id=lead_id,
                        user_id=current_user.id,
                        role='model',
                        content=full_ai_response
                    )
                    db.session.add(new_ai_message)
                    db.session.commit()
                
                return app.response_class(stream_with_context(generate_stream()), mimetype='text/plain')
            except Exception as e:
                traceback.print_exc() # This will print the full traceback to the console
                ai_response = f"Error communicating with AI: {str(e)}"
                flash(ai_response, 'error')
                # Save error message to the database
                new_ai_message = ChatMessage(
                    lead_id=lead_id,
                    user_id=current_user.id,
                    role='model',
                    content=ai_response
                )
                db.session.add(new_ai_message)
                db.session.commit()
                return app.response_class(ai_response, mimetype='text/plain'), 500
        
    return render_template('ai_chat.html', lead=lead, chat_history=chat_history)

@app.route('/ai-chat/<int:lead_id>/delete-message/<int:message_id>', methods=['POST'])
@login_required
def delete_chat_message(lead_id, message_id):
    """Delete a specific chat message."""
    message = ChatMessage.query.get_or_404(message_id)
    if message.lead_id != lead_id or message.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(message)
    db.session.commit()
    return jsonify({'success': True}), 200

@app.route('/generate-email-content/<int:lead_id>', methods=['POST'])
@login_required
def generate_email_content(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    data = request.get_json()
    subject = data.get('subject')
    pitch = data.get('pitch')
    tone = data.get('tone', 'neutral')
    length = data.get('length', 'medium')
    key_points = data.get('key_points')
    call_to_action = data.get('call_to_action')

    if not subject or not pitch:
        return jsonify({'error': 'Subject and pitch are required.'}), 400

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Construct the prompt with fine-tuning controls
        email_prompt = f"""
        Generate a professional email for a lead named {lead.full_name or lead.username} ({lead.platform}).
        Here is some information about the lead:
        - Username: {lead.username}
        - Platform: {lead.platform}
        - Full Name: {lead.full_name or 'N/A'}
        - Bio: {lead.bio or 'N/A'}
        - Followers: {lead.followers or 'N/A'}
        - Email: {lead.email or 'N/A'}
        - Website: {lead.website or 'N/A'}
        - Location: {lead.location or 'N/A'}
        - Tags: {', '.join(lead.tags_list) if lead.tags_list else 'N/A'}

        The email subject is: "{subject}"
        The main message/pitch to convey is: "{pitch}"
        The desired tone for the email is: "{tone}".
        The desired length for the email is: "{length}".
        
        Key points to include: "{key_points if key_points else 'None'}"
        Call to action: "{call_to_action if call_to_action else 'None'}"

        Please generate a compelling email body based on the above information and controls.
        """
        response = model.generate_content(email_prompt)
        generated_email_content = response.text
        return jsonify({'email_content': generated_email_content})
    except Exception as e:
        return jsonify({'error': f'Error generating email: {str(e)}'}), 500

@app.route('/send-generated-email/<int:lead_id>', methods=['POST'])
@login_required
def send_generated_email(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    subject = request.form.get('subject')
    body = request.form.get('body')

    if not lead.email:
        return jsonify({'error': 'Lead does not have an email address.'}), 400
    if not subject or not body:
        return jsonify({'error': 'Subject and body are required.'}), 400

    try:
        send_lead_email(lead.id, subject, body) # Reusing existing function
        flash('Email sent successfully!', 'success')
        return jsonify({'success': True})
    except Exception as e:
        flash(f'Error sending email: {str(e)}', 'error')
        return jsonify({'error': f'Error sending email: {str(e)}'}), 500


# ============================================================================
# API Routes
# ============================================================================

@app.route('/api/track-visitor', methods=['POST'])
def api_track_visitor():
    """API: Receive and process website visitor data for lead generation."""
    try:
        data = request.get_json()
        if not data:
            return create_response(error='No data provided', status=400)

        # Extract visitor IP (Flask's request.remote_addr)
        visitor_ip = request.remote_addr
        
        company_name = None
        company_industry = None
        
        # Example: Simple IP-based "enrichment" (very basic, for demonstration)
        if visitor_ip == '127.0.0.1':
            company_name = "Localhost Corp"
            company_industry = "Development"
        else:
            pass

        lead_data = {
            'user_id': current_user.id if current_user.is_authenticated else None,
            'username': f"visitor_{visitor_ip}_{datetime.utcnow().timestamp()}",
            'platform': 'website_visit',
            'full_name': None,
            'bio': f"Website visitor from IP: {visitor_ip}. Visited URL: {data.get('url')}",
            'email': None,
            'website': data.get('url'),
            'location': None,
            'profile_url': data.get('url'),
            'company_name': company_name,
            'company_industry': company_industry,
            'company_size': None,
            'job_title': None,
            'tech_stack': None,
            'engagement_score': 0.0,
            'tags': ['website_visitor']
        }

        # Handle potential duplicates based on IP/session within a certain timeframe
        # Check for existing leads from the same IP within the last 24 hours
        time_threshold = datetime.utcnow() - timedelta(hours=current_app.config['VISITOR_LEAD_DUPLICATE_CHECK_HOURS'])
        existing_lead = Lead.query.filter(
            Lead.bio.ilike(f"%Website visitor from IP: {visitor_ip}%"),
            Lead.created_at >= time_threshold
        ).first()

        try:
            if existing_lead:
                # Update existing lead
                LeadManager.update_lead(existing_lead.id, lead_data)
                return create_response(
                    data={'lead_id': existing_lead.id, 'username': existing_lead.username},
                    message='Visitor data updated successfully',
                    status=200
                )
            else:
                # Create new lead
                lead = LeadManager.create_lead(lead_data)
                return create_response(
                    data={'lead_id': lead.id, 'username': lead.username},
                    message='Visitor data processed and lead created successfully',
                    status=201
                )
        except Exception as e:
            print(f"Error processing lead from visitor data: {e}")
            return create_response(
                error=f'Failed to process lead from visitor data: {str(e)}',
                status=500
            )

    except Exception as e:
        return create_response(
            error=f'An error occurred while tracking visitor: {str(e)}',
            status=500
        )

@app.route('/api/leads', methods=['GET'])
@require_rate_limit(limit=100, window=3600)
def api_get_leads():
    """API: Get all leads with filtering"""
    try:
        # Get parameters
        search_query = request.args.get('search', '')
        platform = request.args.get('platform', None)
        min_followers = int(request.args.get('min_followers', 0))
        min_engagement = float(request.args.get('min_engagement', 0.0))
        limit = min(int(request.args.get('limit', 100)), 1000)  # Max 1000
        offset = int(request.args.get('offset', 0))
        sort_by = request.args.get('sort_by', 'engagement_score')
        
        # Search leads
        leads, total = Lead.search_leads(
            query=search_query,
            platform=platform,
            min_followers=min_followers,
            min_engagement=min_engagement,
            limit=limit,
            offset=offset,
            order_by=sort_by
        )
        
        # Convert to dict
        leads_data = [lead.to_dict() for lead in leads]
        
        return create_response(
            data={
                'leads': leads_data,
                'total': total,
                'limit': limit,
                'offset': offset
            },
            message='Leads retrieved successfully'
        )
        
    except Exception as e:
        return create_response(
            error=str(e),
            status=500
        )


@app.route('/api/leads/<int:lead_id>', methods=['GET'])
@require_rate_limit(limit=100, window=3600)
def api_get_lead(lead_id):
    """API: Get single lead by ID"""
    try:
        lead = Lead.query.get(lead_id)
        
        if not lead:
            return create_response(
                error='Lead not found',
                status=404
            )
        
        return create_response(
            data=lead.to_dict(),
            message='Lead retrieved successfully'
        )
        
    except Exception as e:
        return create_response(
            error=str(e),
            status=500
        )


@app.route('/api/leads', methods=['POST'])
@require_rate_limit(limit=50, window=3600)
def api_create_lead():
    """API: Create new lead"""
    try:
        data = request.get_json()
        
        if not data:
            return create_response(
                error='No data provided',
                status=400
            )
        
        # Validate required fields
        if 'username' not in data or 'platform' not in data:
            return create_response(
                error='Username and platform are required',
                status=400
            )
        
        # Check for duplicate
        existing = Lead.query.filter_by(
            username=data['username'],
            platform=data['platform']
        ).first()
        
        if existing:
            return create_response(
                error='Lead with this username already exists on this platform',
                status=409
            )
        
        # Create lead
        lead = LeadManager.create_lead(data)
        
        return create_response(
            data=lead.to_dict(),
            message='Lead created successfully',
            status=201
        )
        
    except Exception as e:
        return create_response(
            error=str(e),
            status=500
        )


@app.route('/api/leads/<int:lead_id>', methods=['PUT', 'PATCH'])
@require_rate_limit(limit=50, window=3600)
def api_update_lead(lead_id):
    """API: Update existing lead"""
    try:
        data = request.get_json()
        
        if not data:
            return create_response(
                error='No data provided',
                status=400
            )
        
        # Update lead
        lead = LeadManager.update_lead(lead_id, data)
        
        if not lead:
            return create_response(
                error='Lead not found',
                status=404
            )
        
        return create_response(
            data=lead.to_dict(),
            message='Lead updated successfully'
        )
        
    except Exception as e:
        return create_response(
            error=str(e),
            status=500
        )


@app.route('/api/leads/<int:lead_id>', methods=['DELETE'])
@require_rate_limit(limit=50, window=3600)
def api_delete_lead(lead_id):
    """API: Delete lead"""
    try:
        success = LeadManager.delete_lead(lead_id)
        
        if not success:
            return create_response(
                error='Lead not found',
                status=404
            )
        
        return create_response(
            message='Lead deleted successfully'
        )
        
    except Exception as e:
        return create_response(
            error=str(e),
            status=500
        )


@app.route('/api/leads/bulk-delete', methods=['POST'])
@require_rate_limit(limit=20, window=3600)
def api_bulk_delete():
    """API: Bulk delete leads"""
    try:
        data = request.get_json()
        
        if not data or 'lead_ids' not in data:
            return create_response(
                error='lead_ids array is required',
                status=400
            )
        
        lead_ids = data['lead_ids']
        
        if not isinstance(lead_ids, list):
            return create_response(
                error='lead_ids must be an array',
                status=400
            )
        
        count = LeadManager.bulk_delete(lead_ids)
        
        return create_response(
            data={'deleted_count': count},
            message=f'{count} leads deleted successfully'
        )
        
    except Exception as e:
        return create_response(
            error=str(e),
            status=500
        )


@app.route('/api/stats', methods=['GET'])
@require_api_key
@require_rate_limit(limit=100, window=3600)
def api_get_stats():
    """API: Get statistics"""
    try:
        stats = Lead.get_statistics(current_user.id)
        
        # Convert recent leads to dict
        stats['recent_leads'] = [lead.to_dict() for lead in stats['recent_leads']]
        
        return create_response(
            data=stats,
            message='Statistics retrieved successfully'
        )
        
    except Exception as e:
        return create_response(
            error=str(e),
            status=500
        )


@app.route('/api/tags', methods=['GET'])
@require_api_key
@require_rate_limit(limit=100, window=3600)
def api_get_tags():
    """API: Get all unique tags"""
    try:
        tags = Lead.get_all_tags(current_user.id)
        
        return create_response(
            data={'tags': tags},
            message='Tags retrieved successfully'
        )
        
    except Exception as e:
        return create_response(
            error=str(e),
            status=500
        )


@app.route('/api/calculate-engagement', methods=['POST'])
@require_rate_limit(limit=100, window=3600)
def api_calculate_engagement():
    """API: Calculate engagement score"""
    try:
        data = request.get_json()
        
        if not data or 'followers' not in data:
            return create_response(
                error='followers count is required',
                status=400
            )
        
        followers = int(data['followers'])
        avg_likes = int(data.get('avg_likes', 0))
        avg_comments = int(data.get('avg_comments', 0))
        
        score = Lead.calculate_engagement_score(followers, avg_likes, avg_comments)
        
        return create_response(
            data={
                'engagement_score': score,
                'followers': followers,
                'avg_likes': avg_likes,
                'avg_comments': avg_comments
            },
            message='Engagement score calculated successfully'
        )
        
    except ValueError:
        return create_response(
            error='Invalid input values',
            status=400
        )
    except Exception as e:
        return create_response(
            error=str(e),
            status=500
        )


@app.route('/api/docs')
def api_docs():
    """API Documentation page"""
    return render_template('api_docs.html')


# ============================================================================
# API Key Management Routes
# ============================================================================

@app.route('/api/keys', methods=['GET'])
@login_required
def api_keys_list():
    """List all API keys for the current user"""
    api_keys = APIKey.query.filter_by(user_id=current_user.id).all()
    return render_template('api_keys.html', api_keys=api_keys)

@app.route('/api/keys/generate', methods=['POST'])
@login_required
def generate_api_key():
    """Generate a new API key for the current user"""
    try:
        # Generate a new key
        new_key_value = secrets.token_urlsafe(32)
        
        # Set expiration (e.g., 1 year from now)
        expires_at = datetime.utcnow() + timedelta(days=365)

        api_key = APIKey(user_id=current_user.id, key=new_key_value, expires_at=expires_at)
        db.session.add(api_key)
        db.session.commit()
        flash('New API key generated successfully!', 'success')
    except Exception as e:
        flash(f'Error generating API key: {str(e)}', 'error')
    return redirect(url_for('api_keys_list'))

@app.route('/api/keys/<int:key_id>/revoke', methods=['POST'])
@login_required
def revoke_api_key(key_id):
    """Revoke an API key"""
    api_key = APIKey.query.filter_by(id=key_id, user_id=current_user.id).first()
    if api_key:
        api_key.is_active = False
        db.session.commit()
        flash('API key revoked successfully!', 'success')
    else:
        flash('API key not found or you do not have permission to revoke it.', 'error')
    return redirect(url_for('api_keys_list'))


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    if request.path.startswith('/api/'):
        return create_response(
            error='Endpoint not found',
            status=404
        )
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors"""
    if request.path.startswith('/api/'):
        return create_response(
            error='Internal server error',
            status=500
        )
    return render_template('500.html'), 500


@app.errorhandler(429)
def rate_limit_exceeded(e):
    """Handle rate limit errors"""
    return create_response(
        error='Rate limit exceeded. Please try again later.',
        status=429
    )


# ============================================================================
# CLI Commands
# ============================================================================

@app.cli.command()
def init_db():
    """Initialize the database."""
    db.create_all()
    print('Database initialized!')


@app.cli.command()
def seed_db():
    """Seed database with sample data."""
    sample_leads = [
        {
            'username': 'tech_guru',
            'platform': 'instagram',
            'full_name': 'Sarah Tech',
            'bio': 'Tech reviews and tutorials | DM for collabs',
            'followers': 25000,
            'email': 'sarah@techguru.com',
            'location': 'San Francisco, CA',
            'profile_url': 'https://instagram.com/tech_guru',
            'engagement_score': 45.5,
            'tags': ['tech', 'influencer', 'reviews']
        },
        {
            'username': 'fitness_pro',
            'platform': 'twitter',
            'full_name': 'Mike Fitness',
            'bio': 'Certified personal trainer | Online coaching',
            'followers': 15000,
            'email': 'mike@fitnesspro.com',
            'location': 'Los Angeles, CA',
            'profile_url': 'https://twitter.com/fitness_pro',
            'engagement_score': 38.2,
            'tags': ['fitness', 'health', 'coaching']
        },
        {
            'username': 'food_blogger',
            'platform': 'instagram',
            'full_name': 'Emma Food',
            'bio': 'Food blogger | Restaurant reviews',
            'followers': 50000,
            'email': 'emma@foodblog.com',
            'location': 'New York, NY',
            'profile_url': 'https://instagram.com/food_blogger',
            'engagement_score': 62.8,
            'tags': ['food', 'blogger', 'restaurants']
        }
    ]
    
    for lead_data in sample_leads:
        try:
            LeadManager.create_lead(lead_data)
            print(f"Created lead: {lead_data['username']}")
        except:
            print(f"Skipped (already exists): {lead_data['username']}")
    
    print('Database seeded!')


# ============================================================================
# Email Functions
# ============================================================================

def send_lead_email(lead_id, subject, message):
    lead = Lead.query.get(lead_id)
    
    if not lead.email:
        return False
    
    msg = Message(
        subject=subject,
        recipients=[lead.email],
        html=message
    )
    
    app.mail.send(msg)
    
    # Log email
    email_log = EmailLog(
        lead_id=lead_id,
        user_id=current_user.id,
        subject=subject,
        body=message,
        status='sent'
    )
    db.session.add(email_log)
    db.session.commit()
    
    return True

# ============================================================================
# CRM Integration Functions
# ============================================================================

def sync_to_salesforce(lead):
    try:
        sf = Salesforce(
            username=app.config['SALESFORCE_USERNAME'],
            password=app.config['SALESFORCE_PASSWORD'],
            security_token=app.config['SALESFORCE_TOKEN']
        )
        
        # Prepare lead data for Salesforce
        first_name = lead.full_name.split() if lead.full_name else ''
        last_name = lead.full_name.split()[-1] if lead.full_name else lead.username
        
        # Create lead in Salesforce
        result = sf.Lead.create({
            'FirstName': first_name,
            'LastName': last_name,
            'Company': 'Unknown', # Default company, can be customized
            'Email': lead.email,
            'Status': 'Open',
            'LeadSource': lead.platform
        })
        
        # Store Salesforce ID
        lead.salesforce_id = result['id']
        db.session.commit()
        
        flash(f'Lead {lead.username} synced to Salesforce with ID: {result["id"]}', 'success')
        return result['id']
    
    except Exception as e:
        flash(f'Error syncing lead {lead.username} to Salesforce: {str(e)}', 'error')
        print(f"Salesforce sync error: {e}")
        return None

def sync_to_hubspot(lead):
    try:
        client = HubSpot(access_token=app.config['HUBSPOT_API_KEY'])
        
        properties = {
            "email": lead.email,
            "firstname": lead.full_name.split() if lead.full_name else '',
            "lastname": lead.full_name.split()[-1] if lead.full_name else lead.username,
            "website": lead.website,
            "company": lead.platform
        }
        
        simple_public_object_input = SimplePublicObjectInput(properties=properties)
        
        api_response = client.crm.contacts.basic_api.create(
            simple_public_object_input=simple_public_object_input
        )
        
        # Store HubSpot ID
        lead.hubspot_id = api_response.id
        db.session.commit()
        
        flash(f'Lead {lead.username} synced to HubSpot with ID: {api_response.id}', 'success')
        return api_response.id
    
    except Exception as e:
        flash(f'Error syncing lead {lead.username} to HubSpot: {str(e)}', 'error')
        print(f"HubSpot sync error: {e}")
        return None

def fetch_twitter_lead(username):
    # Setup API
    auth = tweepy.OAuthHandler(
        app.config['TWITTER_API_KEY'],
        app.config['TWITTER_API_SECRET']
    )
    auth.set_access_token(
        app.config['TWITTER_ACCESS_TOKEN'],
        app.config['TWITTER_ACCESS_TOKEN_SECRET']
    )
    
    api = tweepy.API(auth)
    
    # Get user info
    user = api.get_user(screen_name=username)
    
    # Create lead
    lead_data = {
        'username': user.screen_name,
        'platform': 'twitter',
        'full_name': user.name,
        'bio': user.description,
        'followers': user.followers_count,
        'following': user.friends_count,
        'location': user.location,
        'profile_url': f'https://twitter.com/{user.screen_name}',
        'website': user.url
    }
    
    return LeadManager.create_lead(lead_data, current_user.id)

def fetch_instagram_lead(username):
    cl = Client()
    cl.login(
        app.config['INSTAGRAM_USERNAME'],
        app.config['INSTAGRAM_PASSWORD']
    )
    
    # Get user info
    user_id = cl.user_id_from_username(username)
    user_info = cl.user_info(user_id)
    
    # Create lead
    lead_data = {
        'username': user_info.username,
        'platform': 'instagram',
        'full_name': user_info.full_name,
        'bio': user_info.biography,
        'followers': user_info.follower_count,
        'following': user_info.following_count,
        'profile_url': f'https://instagram.com/{user_info.username}',
        'website': user_info.external_url
    }
    
    return LeadManager.create_lead(lead_data, current_user.id)

# ============================================================================
# Gemini API Integration
# ============================================================================

def generate_leads_with_gemini(prompt):
    api_key = app.config['GOOGLE_GEMINI_API_KEY']
    if not api_key:
        flash("Google Gemini API key is not configured.", "error")
        print("Google Gemini API key is not configured.")
        return []

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')

    # Craft the prompt for lead generation
    full_prompt = f"""
    Generate a list of potential leads based on the following criteria: "{prompt}".
    **Important**: Before including a lead, please perform a quick check to ensure the social media profile (e.g., Twitter, Instagram handle) exists.
    For each lead, provide the following information in a JSON format:
    {{
        "username": "unique_username",
        "platform": "platform_name (e.g., twitter, instagram, linkedin)",
        "full_name": "Full Name",
        "bio": "Short biography or description",
        "followers": "Number of followers (integer)",
        "email": "email@example.com (if available, otherwise null)",
        "website": "https://example.com (if available, otherwise null)",
        "location": "City, Country (if available, otherwise null)",
        "profile_url": "https://platform.com/username",
        "engagement_score": "Engagement score (float, e.g., 0.0-100.0)",
        "tags": ["tag1", "tag2"],
        "company_name": "Company Name (if available, otherwise null)",
        "company_industry": "Industry (if available, otherwise null)",
        "company_size": "Company Size (e.g., '1-10', '11-50', '51-200', '201-500', '501-1000', '1001+ employees', otherwise null)",
        "job_title": "Job Title (if available, otherwise null)",
        "tech_stack": ["tech1", "tech2"] (list of technologies, if available, otherwise null)
    }}
    Provide only the JSON array of lead objects, without any additional text or markdown.
    Generate at least 3 leads that you have verified are real accounts.
    """

    try:
        response = model.generate_content(full_prompt)
        raw_response_text = response.text
        print(f"Raw Gemini API response: {raw_response_text}") # Debugging line
        
        # Extract JSON from the response text, which may be wrapped in markdown
        json_match = re.search(r"```json\n(.*)\n```", raw_response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Fallback for cases where the response is just the JSON object
            json_text = raw_response_text.strip()

        leads_data = json.loads(json_text)
        
        # Return the raw lead data instead of creating Lead objects here
        leads_to_return = []
        for lead_data in leads_data:
            # Basic validation and cleaning
            if 'username' in lead_data and 'platform' in lead_data:
                lead_data['followers'] = lead_data.get('followers', 0)
                lead_data['engagement_score'] = lead_data.get('engagement_score', 0.0)
                lead_data['tags'] = lead_data.get('tags', [])
                leads_to_return.append(lead_data)
        
        return leads_to_return
    except Exception as e:
        flash(f"Error generating leads with Gemini API: {str(e)}", "error")
        print(f"Gemini API error: {e}")
        return []

 # ============================================================================
 # Run Application
# ============================================================================

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )