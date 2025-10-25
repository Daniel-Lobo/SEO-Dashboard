# SEO Dashboard

A comprehensive AI-powered SEO content management and automation platform designed to streamline content creation, keyword research, topic clustering, and SEO optimization workflows.

---

## ⚠️ IMPORTANT NOTICE

### **This software was developed under contract for a client and is shared here solely as a portfolio demonstration of my technical capabilities. The code is proprietary and not licensed for use, modification, or distribution by others. All rights remain with the original client. This repository is for viewing purposes only.**

---

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10.12-blue)
![Flask](https://img.shields.io/badge/flask-3.0.1-green)

## 📋 Table of Contents

- [Overview](#overview)
- [Coding Conventions](#coding-conventions)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Deployment](#deployment)

## 🎯 Overview

The SEO Dashboard is an enterprise-grade platform that leverages multiple AI providers (OpenAI, Anthropic, Google Gemini, OpenRouter) to automate and optimize SEO content workflows. It provides tools for content creation, outline generation, topic clustering, keyword analysis, and guest posting management.

## 📝 Coding Conventions

The project has a unique architecture where **all CSS and JavaScript code is embedded within HTML files** rather than separated into individual `.css` or `.js` files. However, it follows a **strict naming convention** that makes it easy to locate where any function or class is defined.

### Naming Conventions

#### JavaScript Functions
- **Format**: `PageName_FunctionName()`
- **Example**: `ContentCreator_GenerateArticle()`, `ClusterCreator_AddKeyword()`
- **Location**: Found in `/dashboard/HTML/PageName.html`

#### CSS Classes
- **Format**: `page-name-element-description`
- **Example**: `.content-creator-button-primary`, `.cluster-creator-input-field`
- **Location**: Within `<style>` tags in `/dashboard/HTML/PageName.html`

#### Element IDs
- **Format**: `PageName-ElementPurpose`
- **Example**: `#ContentCreator::KeywordInput`, `#ClusterCreator::SaveButton`
- **Convention**: PascalCase for page name, PascalCase for element purpose
- **Location**: HTML elements within `/dashboard/HTML/PageName.html`

#### Route Naming
- **Format**: `/module_name-action_name`
- **Example**: `/content_creator-get_blacklisted_words`, `/topic_cluster-generate_entities`
- **Backend**: Defined in corresponding Python modules (e.g., `content_creator.py`)

### File Organization

All HTML templates are located in `/dashboard/HTML/` and contain:
- **Structure** (HTML markup)
- **Styling** (`<style>` blocks)
- **Behavior** (`<script>` blocks)

This monolithic approach allows for:
- Quick prototyping and iteration
- Self-contained components
- Easy debugging (everything in one place)
- Reduced file switching during development

### Example Structure

```html
<!-- /dashboard/HTML/ContentCreator.html -->
<style>
    .content-creator-header { /* styles here */ }
    .content-creator-button { /* styles here */ }
</style>

<script>
    function ContentCreator_Init() { /* logic here */ }
    function ContentCreator_GenerateArticle() { /* logic here */ }
</script>
```

### Built For

- **Content Marketers**: Streamline content creation with AI-powered assistance
- **SEO Specialists**: Manage keywords, clusters, and optimization strategies
- **Digital Agencies**: Multi-client support with role-based access control
- **Content Teams**: Collaborative tools for planning and executing content strategies

## ✨ Key Features

### 🤖 AI-Powered Content Creation

- **Multi-Provider AI Support**: OpenAI GPT-4, Anthropic Claude, Google Gemini, and OpenRouter
- **Intelligent Content Generation**: Context-aware article writing with SEO optimization
- **Outline Generator**: Automated content structure creation based on SERP analysis
- **Self-Reference Detection**: Automatically removes self-promotional content
- **Blacklist Management**: Filter out unwanted terms and phrases

### 📊 Topic Clustering & Analysis

- **Entity Analysis**: Extract and analyze core entities and contextual frames
- **Semantic Relationship Mapping**: Understand connections between topics
- **Cluster Creator**: Organize content around topic clusters for better SEO
- **Keyword Grouping**: Intelligently group related keywords

### 🔍 SEO Tools

- **SERP Analysis**: Integrate with ValueSERP API for competitive analysis
- **Internal Linking**: Contextual bridge creation for better site architecture
- **Domain Filtering**: Multi-domain support for agency workflows
- **Keyword Research**: Advanced keyword analysis and tracking

### 📝 Content Management

- **Guest Posting Module**: Manage outreach and content placement
- **CTA Management**: Create and manage call-to-action templates
- **Content Versioning**: Track changes and improvements
- **Multi-Language Support**: Generate content for different markets

### 👥 User Management

- **Role-Based Access Control**: Admin and user permission levels
- **Multi-User Support**: Team collaboration features
- **Activity Logging**: Track all user actions and changes
- **Client Management**: Organize work by client/domain

### 📈 Advanced Features

- **Real-Time Progress Tracking**: Monitor content generation status
- **Fine-Tuning Dataset Creation**: Prepare training data for custom models
- **Similarity Analysis**: Compare content similarity using sentence transformers
- **PDF/Document Processing**: Extract content from various file formats
- **Diff Viewer**: Compare content versions with wikEd diff integration

## 🏗️ Architecture

The application follows a Flask-based architecture with asynchronous processing capabilities:

```
┌─────────────────────────────────────────────────────────┐
│                     Flask Web Server                     │
│                    (Multi-threaded)                      │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
    ┌────▼───┐  ┌────▼────┐  ┌───▼────┐
    │ Auth   │  │ API     │  │ WebUI  │
    │ Layer  │  │ Routes  │  │ Layer  │
    └────┬───┘  └────┬────┘  └───┬────┘
         │           │            │
         └───────────┼────────────┘
                     │
         ┌───────────▼────────────┐
         │   Business Logic Layer  │
         │  - Content Creator      │
         │  - Topic Clustering     │
         │  - Outline Generator    │
         │  - Guest Posting        │
         └───────────┬────────────┘
                     │
         ┌───────────▼────────────┐
         │    Data Access Layer    │
         │  - SQLAlchemy (MySQL)   │
         │  - SQLite (Legacy)      │
         └───────────┬────────────┘
                     │
         ┌───────────▼────────────┐
         │   External Services     │
         │  - OpenAI               │
         │  - Anthropic            │
         │  - Google Gemini        │
         │  - OpenRouter           │
         │  - ValueSERP API        │
         └─────────────────────────┘
```

## 🛠️ Tech Stack

### Backend

- **Framework**: Flask 3.0.1 with async support
- **Database**: 
  - MySQL (Primary via SQLAlchemy)
  - SQLite (Legacy support)
- **ORM**: Flask-SQLAlchemy 3.1.1
- **Authentication**: Flask-Login 0.6.3
- **Async I/O**: aiohttp, aiofile

### AI & NLP

- **AI Providers**: 
  - OpenAI GPT-4 (openai==0.28)
  - Anthropic Claude (anthropic==0.47.2)
  - Google Gemini (google-genai==1.3.0)
- **NLP**: 
  - NLTK 3.8.1
  - Sentence Transformers 2.3.1
  - tiktoken 0.8.0

### Data Processing

- **Document Processing**: 
  - PyMuPDF 1.24.5
  - pdf2image 1.17.0
  - BeautifulSoup4
- **Data Analysis**: 
  - Pandas 2.2.2
  - openpyxl 3.1.4

### Frontend

- **Template Engine**: Jinja2 (via Flask)
- **CSS Framework**: Custom (Azia theme)
- **JavaScript**: Vanilla JS with async/await

### Deployment

- **Containerization**: Docker
- **Platform Support**: Cloudron-ready
- **Web Server**: Flask development server (production-ready alternatives recommended)

## 📦 Installation

### Prerequisites

- Python 3.10.12 or higher
- MySQL database
- API Keys for:
  - OpenAI (optional)
  - Anthropic (optional)
  - Google Gemini (optional)
  - OpenRouter (optional)
  - ValueSERP (for SERP analysis)

### Local Setup

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/SEO-Dashboard.git
cd SEO-Dashboard
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r dashboard/requirements.txt
```

4. **Set up environment variables**

Create a `.env` file in the root directory:

```env
# Flask Configuration
COOKIE_SECRET=your-secret-key-here

# Database
DATABASE_URL=mysql://user:password@localhost/seo_dashboard

# Admin Credentials
ADMIN_PASSWORD=your-admin-password

# AI API Keys
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
OPEN_ROUTER_KEY=your-openrouter-key
GOOGLE_API_KEY=your-google-key

# SERP API
VALUE_SERP_API_KEY=your-valueserp-key

# Logging (optional)
LOG_BASE_URL=http://your-log-server
```

5. **Initialize the database**

```bash
# The application will auto-create tables on first run
python -c "from dashboard.database import Database; Database('./dashboard/')"
```

6. **Run the application**

```bash
chmod +x start.sh
./start.sh
```

The application will be available at `http://localhost:5000`

### Docker Installation

1. **Build the Docker image**

```bash
docker build -t seo-dashboard .
```

2. **Run the container**

```bash
docker run -d \
  -p 5000:5000 \
  -e COOKIE_SECRET=your-secret \
  -e ADMIN_PASSWORD=your-password \
  -e DATABASE_URL=mysql://user:pass@host/db \
  -e OPENAI_API_KEY=your-key \
  --name seo-dashboard \
  seo-dashboard
```

### Cloudron Deployment

The application includes a CloudronManifest.json for easy deployment:

```bash
cloudron install --appstore-id com.flawlessmarketing.dashboard
```

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `COOKIE_SECRET` | Yes | Flask session secret key |
| `ADMIN_PASSWORD` | Yes | Initial admin password |
| `DATABASE_URL` | Yes | MySQL connection string |
| `OPENAI_API_KEY` | No | OpenAI API access |
| `ANTHROPIC_API_KEY` | No | Anthropic Claude access |
| `GOOGLE_API_KEY` | No | Google Gemini access |
| `OPEN_ROUTER_KEY` | No | OpenRouter API access |
| `VALUE_SERP_API_KEY` | No | SERP analysis features |
| `LOG_BASE_URL` | No | External logging endpoint |

### Database Configuration

The application supports both MySQL (recommended) and SQLite:

**MySQL** (Production):
```python
DATABASE_URL=mysql://username:password@hostname:3306/database_name
```

**SQLite** (Development):
- Automatically uses `dump.db` if MySQL is not configured

### User Roles & Permissions

- **Admin** (0xffffffff): Full access to all features
- **User** (Custom): Configurable access flags

## 📖 Usage

### Creating Your First Content

1. **Login** with admin credentials (admin@admin / your-admin-password)
2. **Add Keywords** in the Keywords section
3. **Create Topic Clusters** for organizing content
4. **Generate Outlines** using SERP data
5. **Create Content** with AI assistance
6. **Manage Blacklists** to filter unwanted terms

### Content Creation Workflow

```mermaid
graph LR
    A[Keyword Research] --> B[Topic Clustering]
    B --> C[Entity Analysis]
    C --> D[Outline Generation]
    D --> E[Content Creation]
    E --> F[Self-Reference Removal]
    F --> G[Blacklist Filtering]
    G --> H[Final Article]
```

### API Usage

The dashboard exposes RESTful endpoints for integration:

```python
# Example: Get blacklisted words
import requests

response = requests.post(
    'http://localhost:5000/content_creator-get_blacklisted_words?list=Articles',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)
blacklist = response.json()['Reply']
```

## 🔌 API Endpoints

### Content Creation

- `POST /content_creator-get_blacklisted_words?list={type}` - Retrieve blacklists
- `POST /content_creator-set_blacklisted_words?list={type}` - Update blacklists

### Topic Clustering

- Topic cluster generation endpoints
- Entity analysis endpoints
- Semantic relationship mapping

### Outline Generation

- SERP-based outline creation
- Competitor analysis
- H2/H3 structure extraction

### User Management

- User CRUD operations
- Permission management
- Client/domain assignment

### Guest Posting

- Outreach management
- Content placement tracking
- Link building workflows

*(Full API documentation available in `/docs/api.md`)*

## 📁 Project Structure

```
SEO-Dashboard/
├── dashboard/                    # Main application package
│   ├── __init__.py
│   ├── app.py                   # Flask app initialization
│   ├── alchemy.py               # SQLAlchemy models
│   ├── database.py              # Legacy SQLite database
│   ├── constants.py             # Application constants
│   ├── admin.py                 # Admin routes
│   ├── ChatGpt.py               # AI provider integrations
│   ├── content_creator.py       # Content generation logic
│   ├── topic_cluster_creator.py # Topic clustering
│   ├── OutlineGen.py            # Outline generation
│   ├── guest_posting.py         # Guest post management
│   ├── similarity.py            # Content similarity analysis
│   ├── dataset_tunning.py       # Fine-tuning data prep
│   ├── requirements.txt         # Python dependencies
│   ├── HTML/                    # Frontend templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── ContentCreator.html
│   │   ├── ClusterCreator.html
│   │   └── ...
│   ├── static/                  # Static assets
│   │   ├── css/
│   │   ├── img/
│   │   └── azia/                # UI theme
│   ├── resources/               # Configuration files
│   │   ├── blacklisted_words.txt
│   │   ├── default_prompts.txt
│   │   └── legacy_prompts.txt
│   └── data/                    # Runtime data
│       └── dump_alchemy.db
├── Dockerfile                   # Container definition
├── CloudronManifest.json        # Cloudron deployment config
├── start.sh                     # Startup script
├── deploy.sh                    # Deployment automation
├── export_database.sh           # Database backup script
└── readme.md                    # This file
```

## 🚀 Deployment

### Production Recommendations

Deployment was done with [Cloudron](https://www.cloudron.io/). Please check the CloudronManifest.json file and Cloudron's documentation

### Development Setup

```bash
# Install development dependencies
pip install -r dashboard/requirements.txt

# and you'll also need a MySql server running locally
```



**Made with ❤️ by Daniel Lobo**