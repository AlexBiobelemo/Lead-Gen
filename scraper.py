import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

def _extract_social_media_info(url):
    """Attempts to extract social media platform and username from a URL."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    path_parts = [part for part in parsed_url.path.split('/') if part]

    if 'twitter.com' in domain:
        platform = 'twitter'
        username = path_parts if path_parts else None
    elif 'instagram.com' in domain:
        platform = 'instagram'
        username = path_parts if path_parts else None
    elif 'linkedin.com' in domain:
        platform = 'linkedin'
        # LinkedIn profiles are typically /in/username or /pub/username
        if len(path_parts) >= 2 and path_parts == 'in':
            username = path_parts
        elif len(path_parts) >= 2 and path_parts == 'pub':
            username = path_parts
        elif len(path_parts) >= 1 and path_parts not in ['company', 'jobs', 'feed']: # Direct profile link
            username = path_parts
        else:
            username = None # Cannot reliably extract username for other LinkedIn URLs
    elif 'facebook.com' in domain:
        platform = 'facebook'
        username = path_parts if path_parts else None
    elif 'tiktok.com' in domain:
        platform = 'tiktok'
        username = path_parts if path_parts else None
    elif 'youtube.com' in domain:
        platform = 'youtube'
        # YouTube channels can be /user/ or /channel/
        if len(path_parts) >= 2 and (path_parts == 'user' or path_parts == 'channel'):
            username = path_parts
        else:
            username = path_parts if path_parts else None
    else:
        platform = 'other'
        username = None # Cannot reliably extract username for generic 'other'
    
    # Ensure username is a string
    if isinstance(username, list):
        username = '_'.join(username) # Join list parts with underscore

    return platform, username

def _extract_company_info(soup):
    """Attempts to extract company name and industry from a webpage."""
    company_name = None
    company_industry = None

    # Try to get company name from title or meta tags
    if soup.title and soup.title.string:
        company_name = soup.title.string.split('|').strip()
    
    meta_description = soup.find('meta', attrs={'name': 'description'})
    if meta_description and meta_description.get('content'):
        # Simple heuristic: look for keywords in description
        description = meta_description['content'].lower()
        if 'software' in description or 'tech' in description:
            company_industry = 'Technology'
        elif 'finance' in description or 'bank' in description:
            company_industry = 'Finance'
        # Add more industry heuristics as needed

    og_site_name = soup.find('meta', attrs={'property': 'og:site_name'})
    if og_site_name and og_site_name.get('content'):
        company_name = og_site_name['content'].strip()

    return company_name, company_industry

def _extract_tech_stack(soup):
    """Attempts to identify technologies used on a webpage."""
    tech_stack = []
    text = soup.get_text().lower()

    # Look for common CMS/framework footprints
    if re.search(r'wp-content|wordpress', text):
        tech_stack.append('WordPress')
    if re.search(r'shopify\.com', text) or soup.find('link', href=re.compile(r'cdn\.shopify\.com')):
        tech_stack.append('Shopify')
    if soup.find('script', src=re.compile(r'react(\.production)?\.min\.js')):
        tech_stack.append('React')
    if soup.find('script', src=re.compile(r'vue(\.min)?\.js')):
        tech_stack.append('Vue.js')
    if soup.find('script', src=re.compile(r'angular(\.min)?\.js')):
        tech_stack.append('Angular')
    if soup.find('meta', attrs={'name': 'generator', 'content': re.compile(r'Joomla', re.IGNORECASE)}):
        tech_stack.append('Joomla')
    
    # Look for analytics/marketing tools
    if re.search(r'google-analytics\.com/analytics\.js', text) or re.search(r'gtag\.js', text):
        tech_stack.append('Google Analytics')
    if re.search(r'facebook\.com/tr', text):
        tech_stack.append('Facebook Pixel')

    return list(set(tech_stack)) # Return unique technologies

def scrape_leads(url):
    """
    Scrapes leads from a given URL, attempting to extract comprehensive information.
    """
    leads = []
    
    # Prepend https:// if missing
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Use a dict to avoid duplicate leads based on a primary identifier (e.g., email or username)
        potential_leads_data = {}

        # 1. Extract Email Addresses from text and mailto links
        email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found_emails = set(re.findall(email_regex, response.text))
        
        for email in found_emails:
            if email not in potential_leads_data:
                potential_leads_data[email] = {'email': email, 'platform': 'email', 'profile_url': f'mailto:{email}'}

        # 2. Extract Phone Numbers from text
        phone_regex = r'\b(?:\d{3}[-.]?\d{3}[-.]?\d{4}|\(\d{3}\)\s*\d{3}[-.]?\d{4})\b'
        found_phones = set(re.findall(phone_regex, response.text))
        
        for phone in found_phones:
            # For simplicity, adding as new lead if not associated with an existing email lead
            # A more sophisticated approach would try to link phones to existing leads
            if not any(lead.get('phone') == phone for lead in potential_leads_data.values()):
                # Create a unique key for phone leads if no email/username
                phone_key = f"phone_{phone}"
                potential_leads_data[phone_key] = {'phone': phone, 'platform': 'phone'}


        # 3. Extract Social Media Profiles from links
        all_links = soup.find_all('a', href=True)
        social_platforms_domains = ['twitter.com', 'instagram.com', 'linkedin.com', 'facebook.com', 'tiktok.com', 'youtube.com']

        for link in all_links:
            href = link['href']
            text = link.get_text(strip=True)

            if any(domain in href for domain in social_platforms_domains):
                platform, username = _extract_social_media_info(href)
                if username:
                    # Use a combination of platform and username as a unique key
                    social_key = f"{platform}_{username}"
                    if social_key not in potential_leads_data:
                        lead_entry = {
                            'username': username,
                            'platform': platform,
                            'profile_url': href,
                            'full_name': text if text and len(text) < 50 else None # Heuristic for full name
                        }
                        potential_leads_data[social_key] = lead_entry
                    else:
                        # Update existing entry if more info is found (e.g., full_name)
                        if not potential_leads_data[social_key].get('full_name') and text and len(text) < 50:
                            potential_leads_data[social_key]['full_name'] = text

        # Convert dictionary to list of leads
        leads = list(potential_leads_data.values())

        # Add some default/placeholder values for other fields and refine existing ones
        # Extract company and tech stack info once per URL
        company_name, company_industry = _extract_company_info(soup)
        tech_stack = _extract_tech_stack(soup)

        for lead in leads:
            lead.setdefault('full_name', None)
            lead.setdefault('bio', None)
            lead.setdefault('followers', 0)
            lead.setdefault('email', None)
            lead.setdefault('website', None)
            lead.setdefault('location', None)
            lead.setdefault('engagement_score', 0.0)
            lead.setdefault('tags', ['scraped'])
            lead.setdefault('company_name', company_name)
            lead.setdefault('company_industry', company_industry)
            lead.setdefault('company_size', None) # Cannot reliably scrape, leave for enrichment
            lead.setdefault('job_title', None) # Cannot reliably scrape, leave for enrichment
            lead.setdefault('tech_stack', tech_stack)
            
            # Attempt to set a username if it's missing but profile_url exists
            if not lead.get('username') and lead.get('profile_url'):
                _, inferred_username = _extract_social_media_info(lead['profile_url'])
                if inferred_username:
                    lead['username'] = inferred_username
            
            # If still no username and it's an email lead, use email prefix
            if not lead.get('username') and lead.get('email') and lead.get('platform') == 'email':
                lead['username'] = lead['email'].split('@') # Get prefix only
            
            # If still no platform, default to 'website' if profile_url is not social
            if not lead.get('platform') and lead.get('profile_url') and not any(p in lead['profile_url'] for p in social_platforms_domains):
                lead['platform'] = 'website'
            elif not lead.get('platform') and lead.get('phone'): # For phone-only leads
                lead['platform'] = 'phone'
            elif not lead.get('platform'):
                lead['platform'] = 'unknown'

    except requests.exceptions.RequestException as e:
        print(f"Error scraping {url}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during scraping {url}: {e}")
    
    return leads
