#!/usr/bin/env python3
"""
Arcade Flow Analysis Script

This script analyzes an Arcade flow JSON file and generates a comprehensive
markdown report with user interactions, summary, and social media image.

Usage:
    python analyze_flow.py <flow.json>
    python analyze_flow.py flow.json
"""

import json
import os
import sys
import hashlib
import shutil
import requests
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Configuration
CACHE_DIR = 'cache'
OUTPUT_DIR = 'output'
IMAGES_DIR = os.path.join(OUTPUT_DIR, 'images')


def setup_directories():
    """Create necessary directories"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)


def get_cache_key(prefix, data_string):
    """Create a cache key"""
    cache_string = f"{prefix}_{data_string}"
    return hashlib.md5(cache_string.encode()).hexdigest()


def get_cached_item(cache_key, item_type='description'):
    """Check if we have a cached item"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
            if item_type == 'description':
                return cache_data.get('description')
            elif item_type == 'summary':
                return cache_data.get('summary')
            elif item_type == 'image':
                filename = cache_data.get('filename')
                if filename and os.path.exists(filename):
                    return filename, cache_data.get('url')
    return None


def cache_item(cache_key, item, item_type='description'):
    """Save item to cache"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    with open(cache_file, 'w') as f:
        if item_type == 'description':
            json.dump({'description': item}, f)
        elif item_type == 'summary':
            json.dump({'summary': item}, f)
        elif item_type == 'image':
            json.dump({
                'filename': item[0],
                'url': item[1],
                'created': datetime.now().isoformat()
            }, f)


def describe_interaction(client, step):
    """Use AI to create a human-readable description of the user interaction"""
    click_context = step.get('clickContext', {})
    page_context = step.get('pageContext', {})
    
    # Build context for AI
    clicked_element = click_context.get('text', 'N/A')
    element_type = click_context.get('elementType', 'unknown')
    page_title = page_context.get('title', '')
    page_url = page_context.get('url', '')
    
    # Check cache
    cache_key = get_cache_key('interaction', f"{step.get('id', '')}_{clicked_element}")
    cached = get_cached_item(cache_key, 'description')
    if cached:
        return cached
    
    prompt = f"""Given this user interaction data from a web flow:
- Page: {page_title}
- URL: {page_url}
- Clicked element type: {element_type}
- Clicked element text: {clicked_element}

Create a concise, human-readable description of what the user did. 
Format it as: "Clicked on [action]" or "Interacted with [element]"
Keep it under 20 words and make it natural.

Examples:
- "Clicked on search bar"
- "Selected scooter product"
- "Chose Blue color option"
- "Added item to cart"
- "Clicked on cart icon"

Just return the description, nothing else:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that describes user interactions in simple, clear language."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3
        )
        description = response.choices[0].message.content.strip()
        
        # Cache the result
        cache_item(cache_key, description, 'description')
        return description
    except Exception as e:
        print(f"Error describing interaction: {e}")
        # Fallback to simple description
        if element_type == 'button':
            return f"Clicked on button: {clicked_element}"
        elif element_type == 'image':
            return f"Clicked on image: {clicked_element}"
        elif element_type == 'link':
            return f"Clicked on link: {clicked_element}"
        else:
            return f"Interacted with: {clicked_element}"


def extract_user_interactions(client, flow_data):
    """Extract and describe user interactions"""
    user_interactions = []
    
    for step in flow_data.get('steps', []):
        step_type = step.get('type')
        
        if step_type == 'CHAPTER':
            title = step.get('title', '')
            if title:
                user_interactions.append({
                    'step_number': len(user_interactions) + 1,
                    'action': f"Started: {title}",
                    'type': 'CHAPTER',
                    'description': step.get('subtitle', ''),
                    'page': '',
                    'url': ''
                })
        
        elif step_type in ['IMAGE', 'VIDEO']:
            if 'clickContext' in step:
                action_description = describe_interaction(client, step)
                
                user_interactions.append({
                    'step_number': len(user_interactions) + 1,
                    'action': action_description,
                    'type': step_type,
                    'element': step.get('clickContext', {}).get('text', ''),
                    'page': step.get('pageContext', {}).get('title', ''),
                    'url': step.get('pageContext', {}).get('url', '')
                })
    
    return user_interactions


def generate_flow_summary(client, user_interactions, flow_data):
    """Generate a human-friendly summary of what the user was trying to accomplish"""
    # Check cache
    flow_name = flow_data.get('name', '')
    num_interactions = len(user_interactions)
    cache_key = get_cache_key('summary', f"{flow_name}_{num_interactions}")
    cached = get_cached_item(cache_key, 'summary')
    if cached:
        print("Using cached summary...")
        return cached
    
    # Extract flow metadata
    flow_description = ""
    for step in flow_data.get('steps', []):
        if step.get('type') == 'CHAPTER' and step.get('subtitle'):
            flow_description = step.get('subtitle', '')
            break
    
    # Build actions list
    actions_list = []
    for interaction in user_interactions:
        action_text = interaction.get('action', '')
        page = interaction.get('page', '')
        if page and page not in action_text:
            actions_list.append(f"- {action_text} (on {page})")
        else:
            actions_list.append(f"- {action_text}")
    
    actions_text = "\n".join(actions_list)
    
    prompt = f"""Analyze this user flow and create a clear, readable summary.

Flow: {flow_name}
Description: {flow_description}

User Actions:
{actions_text}

Write a concise 2-3 paragraph summary that:
1. Describes what the user was trying to accomplish
2. Summarizes the key steps they took
3. Notes the final outcome

Use natural, conversational language:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Create clear, engaging summaries of user journeys."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Cache the result
        cache_item(cache_key, summary, 'summary')
        return summary
    except Exception as e:
        print(f"Error generating summary: {e}")
        return f"User completed flow: {flow_name} with {len(user_interactions)} actions."


def generate_image_prompt(flow_summary, flow_data, user_interactions):
    """Create a prompt for image generation"""
    flow_name = flow_data.get('name', 'User Flow')
    
    # Extract key themes
    summary_lower = flow_summary.lower()
    key_themes = []
    if 'scooter' in summary_lower:
        key_themes.append('modern scooter')
    if 'shopping' in summary_lower or 'cart' in summary_lower:
        key_themes.append('online shopping')
    if 'target' in summary_lower:
        key_themes.append('retail shopping experience')
    
    themes_text = ', '.join(key_themes) if key_themes else 'user journey'
    
    prompt = f"""Create a vibrant, professional social media image for this user flow: "{flow_name}"

The image should:
- Be visually engaging and suitable for social media (Instagram, Twitter, LinkedIn)
- Represent the theme of: {themes_text}
- Use modern, clean design with bright, appealing colors
- Have a professional but friendly aesthetic
- Include visual elements that tell a story about the user journey
- Be optimized for 1024x1024 square format
- Look shareable and engaging

Style: Modern digital illustration, clean composition, professional social media graphic design, colorful and eye-catching"""

    return prompt


def generate_social_media_image(client, flow_summary, flow_data, user_interactions):
    """Generate a social media image using DALL·E"""
    # Check cache
    cache_key = get_cache_key('image', f"{flow_data.get('name', '')}_{hashlib.md5(flow_summary.encode()).hexdigest()[:10]}")
    cached = get_cached_item(cache_key, 'image')
    if cached:
        print("Using cached image...")
        return cached
    
    image_prompt = generate_image_prompt(flow_summary, flow_data, user_interactions)
    
    print(f"Generating image...")
    print(f"Prompt preview: {image_prompt[:150]}...\n")
    
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        image_url = response.data[0].url
        
        # Download and save the image
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        
        # Create a descriptive filename
        flow_name_safe = flow_data.get('name', 'flow').replace(' ', '_').replace('/', '_')[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"social_media_image_{flow_name_safe}_{timestamp}.png"
        
        with open(image_filename, 'wb') as f:
            f.write(image_response.content)
        
        result = (image_filename, image_url)
        
        # Cache the result
        cache_item(cache_key, result, 'image')
        
        print(f"✅ Image generated and saved: {image_filename}")
        return result
    
    except Exception as e:
        print(f"❌ Error generating image: {e}")
        print("Make sure you have:")
        print("1. Added 'requests' to requirements.txt")
        print("2. API key has access to DALL·E")
        return None, None


def create_markdown_report(user_interactions, flow_summary, image_filename, flow_data):
    """Create a comprehensive markdown report with all the analysis results"""
    # Extract metadata from flow_data
    upload_id = flow_data.get('uploadId', 'unknown')
    created_by = flow_data.get('createdBy', 'unknown')
    flow_name = flow_data.get('name', 'User Flow')
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Handle image file
    image_path_in_report = None
    if image_filename:
        image_basename = os.path.basename(image_filename)
        source_path = Path(image_filename)
        
        if not source_path.exists():
            source_path = Path(image_basename)
        
        if source_path.exists():
            dest_image_path = Path(IMAGES_DIR) / image_basename
            shutil.copy2(source_path, dest_image_path)
            image_path_in_report = f"images/{image_basename}"
            print(f"✅ Image copied to: {dest_image_path}")
    
    # Create markdown filename
    flow_name_safe = flow_name.replace(' ', '_').replace('/', '_')[:30]
    markdown_filename = f"Flow_Analysis_{flow_name_safe}_{upload_id}_{timestamp}.md"
    markdown_path = Path(OUTPUT_DIR) / markdown_filename
    
    # Generate markdown content
    created_timestamp = flow_data.get('created', {}).get('_seconds')
    created_date = ""
    if created_timestamp:
        try:
            created_date = datetime.fromtimestamp(created_timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except:
            created_date = "N/A"
    else:
        created_date = "N/A"
    
    markdown_content = f"""# Flow Analysis Report

**Flow Name:** {flow_name}  
**Upload ID:** {upload_id}  
**Created By:** {created_by}  
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 📋 Summary

{flow_summary}

---

## 🎯 User Interactions

This section details all the actions the user performed during the flow:

"""
    
    # Add user interactions
    for interaction in user_interactions:
        step_num = interaction.get('step_number', 0)
        action = interaction.get('action', '')
        page = interaction.get('page', '')
        
        markdown_content += f"### {step_num}. {action}\n\n"
        if page:
            markdown_content += f"**Page:** {page}\n\n"
        if interaction.get('url'):
            markdown_content += f"**URL:** {interaction['url']}\n\n"
        markdown_content += "---\n\n"
    
    # Add social media image section
    markdown_content += f"""## 🎨 Social Media Image

"""
    
    if image_path_in_report:
        markdown_content += f"""![Social Media Image]({image_path_in_report})

*Generated image representing the user flow for social media sharing.*

"""
    else:
        markdown_content += "*Image generation was not completed or image file was not found.*\n\n"
    
    # Add metadata/footer
    markdown_content += f"""---

## 📊 Flow Metadata

- **Total Interactions:** {len(user_interactions)}
- **Flow Type:** {flow_data.get('useCase', 'N/A')}
- **Created:** {created_date}
- **Schema Version:** {flow_data.get('schemaVersion', 'N/A')}

---

*Report generated by Arcade Flow Analysis Tool*
"""
    
    # Write markdown file
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"✅ Markdown report created: {markdown_path}")
    return str(markdown_path)


def main():
    """Main function to run the flow analysis"""
    parser = argparse.ArgumentParser(
        description='Analyze an Arcade flow JSON file and generate a comprehensive markdown report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python analyze_flow.py flow.json
  python analyze_flow.py path/to/my_flow.json
        """
    )
    parser.add_argument('flow_file', help='Path to the flow.json file')
    parser.add_argument('--skip-image', action='store_true', help='Skip image generation (faster, lower cost)')
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.flow_file):
        print(f"❌ Error: File not found: {args.flow_file}")
        sys.exit(1)
    
    # Setup
    setup_directories()
    
    # Load flow data
    print(f"📖 Loading flow data from: {args.flow_file}")
    try:
        with open(args.flow_file, 'r', encoding='utf-8') as f:
            flow_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        sys.exit(1)
    
    # Initialize OpenAI client
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please set it in your .env file or environment")
        sys.exit(1)
    
    client = openai.OpenAI(api_key=api_key)
    
    # Step 1: Extract user interactions
    print("\n🔍 Step 1: Identifying user interactions...")
    user_interactions = extract_user_interactions(client, flow_data)
    print(f"   Found {len(user_interactions)} interactions")
    
    # Step 2: Generate summary
    print("\n📝 Step 2: Generating human-friendly summary...")
    flow_summary = generate_flow_summary(client, user_interactions, flow_data)
    print("   Summary generated")
    
    # Step 3: Generate social media image
    image_filename = None
    image_url = None
    if not args.skip_image:
        print("\n🎨 Step 3: Generating social media image...")
        image_filename, image_url = generate_social_media_image(
            client, flow_summary, flow_data, user_interactions
        )
        if image_filename:
            print("   Image generated")
        else:
            print("   ⚠️  Image generation failed")
    else:
        print("\n⏭️  Step 3: Skipping image generation (--skip-image flag set)")
    
    # Step 4: Create markdown report
    print("\n📄 Step 4: Creating markdown report...")
    report_path = create_markdown_report(
        user_interactions, flow_summary, image_filename, flow_data
    )
    
    print(f"\n✅ Analysis complete!")
    print(f"   📁 Report: {report_path}")
    if image_filename:
        print(f"   🖼️  Image: {os.path.join(IMAGES_DIR, os.path.basename(image_filename))}")
    print(f"\n💡 Tip: You can view the report by opening the markdown file")


if __name__ == "__main__":
    main()

