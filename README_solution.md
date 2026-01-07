# Arcade Flow Analysis - Solution Guide

This guide explains how to install, setup, and use the `analyze_flow.py` script to analyze Arcade flow JSON files and generate comprehensive markdown reports.

## 📋 Table of Contents

- [Installation & Setup](#installation--setup)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Caching System](#caching-system)
- [Output Files](#output-files)

## 🔧 Installation & Setup

### Prerequisites

- Python 3.7 or higher
- OpenAI API key

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `openai` - For AI-powered analysis and image generation
- `requests` - For downloading generated images
- `python-dotenv` - For managing environment variables

### Step 2: Configure API Key

1. Create a `.env` file in the project root directory
2. Add your OpenAI API key:

```
OPENAI_API_KEY=your_api_key_here
```

**⚠️ Important:** The `.env` file is already in `.gitignore` to keep your API key secure. Never commit it to version control.

### Step 3: Verify Setup

Make sure your project structure looks like this:

```
arcade-ai-interview/
├── analyze_flow.py          # Main script
├── flow.json                # Input file (your Arcade flow data)
├── requirements.txt         # Python dependencies
├── .env                     # Your API key (not in git)
├── README.md                # Original challenge README
└── README_solution.md       # This file
```

## 🚀 Usage

### Basic Usage

```bash
python analyze_flow.py flow.json
```

### Skip Image Generation (Faster, Lower Cost)

If you want to generate the report without the social media image:

```bash
python analyze_flow.py flow.json --skip-image
```

### Command Line Arguments

- `flow_file` (required): Path to your flow.json file
- `--skip-image` (optional): Skip image generation to save time and API costs

**Examples:**

```bash
# Analyze flow.json in current directory
python analyze_flow.py flow.json

# Analyze a flow file in a different location
python analyze_flow.py path/to/your/flow.json

# Generate report without image
python analyze_flow.py flow.json --skip-image
```

## 🔍 How It Works

The script performs 4 main steps:

### Step 1: Identify User Interactions

**What it does:**
- Parses the flow JSON file to extract all user actions
- Identifies CHAPTER, IMAGE, and VIDEO steps with click contexts
- Uses AI (GPT-4o-mini) to convert raw interaction data into human-readable descriptions

**Example output:**
- "Clicked on search bar"
- "Selected scooter product"
- "Added item to cart"

**Caching:** Each interaction description is cached individually based on the step ID and clicked element text.

### Step 2: Generate Human-Friendly Summary

**What it does:**
- Takes all identified user interactions
- Analyzes the flow metadata (name, description)
- Uses AI (GPT-4o-mini) to create a 2-3 paragraph narrative summary

**The summary includes:**
1. What the user was trying to accomplish
2. Key steps they took
3. Final outcome

**Caching:** The summary is cached based on flow name and number of interactions.

### Step 3: Generate Social Media Image (Optional)

**What it does:**
- Analyzes the flow summary and extracts key themes
- Creates a detailed prompt for image generation
- Uses DALL·E 3 to generate a 1024x1024 professional social media image
- Downloads and saves the image locally

**Caching:** Generated images are cached based on flow name and summary hash.

**Note:** This step can be skipped with `--skip-image` flag to save API costs.

### Step 4: Create Markdown Report

**What it does:**
- Combines all analysis results into a comprehensive markdown file
- Organizes content with proper sections and formatting
- Copies the social media image to the `output/images/` directory
- Links the image in the markdown report

## 💾 Caching System

The script implements intelligent caching to reduce API costs and improve performance:

### Cache Location

All cached data is stored in the `cache/` directory as JSON files.

### What Gets Cached

1. **Interaction Descriptions**
   - Cache key: Based on step ID and clicked element text
   - File: `cache/{hash}.json`
   - Content: Human-readable action descriptions

2. **Flow Summary**
   - Cache key: Based on flow name and number of interactions
   - File: `cache/{hash}.json`
   - Content: Generated summary text

3. **Social Media Images**
   - Cache key: Based on flow name and summary hash
   - File: `cache/{hash}.json` (metadata) + actual PNG file
   - Content: Image filename and URL reference

### Cache Benefits

- **Cost Savings:** Avoid regenerating expensive API responses
- **Speed:** Instant retrieval for previously analyzed flows
- **Development:** Faster iteration when testing script changes

### Cache Management

- Cache files are automatically created and updated
- Old cache entries remain valid unless you delete them manually
- Cache is checked before each API call

**To clear cache:** Simply delete the `cache/` directory or individual cache files.

## 📁 Output Files

### Output Directory Structure

```
output/
├── Flow_Analysis_{flow_name}_{upload_id}_{timestamp}.md
└── images/
    └── social_media_image_{flow_name}_{timestamp}.png
```

### Markdown File Naming

The output markdown file follows this naming convention:

```
Flow_Analysis_{flow_name}_{upload_id}_{timestamp}.md
```

**Components:**
- `Flow_Analysis` - Fixed prefix
- `{flow_name}` - Flow name from JSON (sanitized, max 30 chars)
- `{upload_id}` - Upload ID from flow.json
- `{timestamp}` - Generation timestamp (YYYYMMDD_HHMMSS format)

**Example:**
```
Flow_Analysis_Add_a_Scooter_to_Your_Cart_on__2RnSqfsV4EsODmUiPKoW_20260106_135948.md
```

### Markdown Report Contents

The generated markdown file includes:

1. **Header Section**
   - Flow name
   - Upload ID
   - Created by
   - Generation timestamp

2. **Summary Section**
   - Human-friendly narrative summary of the user journey

3. **User Interactions Section**
   - Numbered list of all user actions
   - Page titles and URLs for each action
   - Detailed descriptions

4. **Social Media Image Section**
   - Embedded image (if generated)
   - Image stored in `output/images/` directory

5. **Flow Metadata Section**
   - Total number of interactions
   - Flow type
   - Creation date
   - Schema version

### Image Storage

- Images are saved with the filename: `social_media_image_{flow_name}_{timestamp}.png`
- Images are stored in `output/images/` directory
- Images are referenced in the markdown with relative paths: `images/{filename}.png`

## 📊 Example Output

After running the script, you'll see output like:

```
📖 Loading flow data from: flow.json

🔍 Step 1: Identifying user interactions...
   Found 9 interactions

📝 Step 2: Generating human-friendly summary...
   Summary generated

🎨 Step 3: Generating social media image...
Generating image...
Prompt preview: Create a vibrant, professional social media image...
✅ Image generated and saved: social_media_image_Add_a_Scooter_to_Your_Cart_on__20260106_135948.png

📄 Step 4: Creating markdown report...
✅ Image copied to: output/images/social_media_image_Add_a_Scooter_to_Your_Cart_on__20260106_135948.png
✅ Markdown report created: output/Flow_Analysis_Add_a_Scooter_to_Your_Cart_on__2RnSqfsV4EsODmUiPKoW_20260106_135948.md

✅ Analysis complete!
   📁 Report: output/Flow_Analysis_Add_a_Scooter_to_Your_Cart_on__2RnSqfsV4EsODmUiPKoW_20260106_135948.md
   🖼️  Image: output/images/social_media_image_Add_a_Scooter_to_Your_Cart_on__20260106_135948.png
```

## 🎯 Tips

1. **First Run:** The first time you run the script on a flow, it will make API calls. Subsequent runs will use cached results and be much faster.

2. **Cost Management:** Use `--skip-image` flag during development/testing to avoid DALL·E API costs.

3. **Viewing Reports:** Open the generated markdown file in any markdown viewer or GitHub to see the formatted report with images.

4. **Multiple Flows:** The script works with any Arcade flow JSON file - just change the input file path.

5. **Cache Sharing:** Cache files can be shared across team members to avoid redundant API calls (be careful not to commit API keys).

## 🔒 Security Notes

- Never commit your `.env` file to version control
- The `.gitignore` file already excludes `.env`, `cache/`, and `output/` directories
- API keys are only read from environment variables, never hardcoded

## ❓ Troubleshooting

**Error: OPENAI_API_KEY not found**
- Make sure you have a `.env` file in the project root
- Verify the file contains: `OPENAI_API_KEY=your_key_here`

**Error: File not found**
- Check that the path to your flow.json file is correct
- Use absolute paths if relative paths don't work

**Error generating image**
- Verify your OpenAI API key has access to DALL·E
- Check your API usage limits
- Try using `--skip-image` to generate the report without an image

**Cache not working**
- Ensure the `cache/` directory exists and is writable
- Check file permissions

---

*Happy analyzing! 🚀*

